"""LangGraph Agent built on Deep Agents with DB query and internet search."""

from pathlib import Path
from typing import AsyncGenerator, Optional
from urllib.parse import quote_plus

from deepagents import create_deep_agent
import deepagents.graph as deepagents_graph
from deepagents.backends.filesystem import FilesystemBackend
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from psycopg_pool import AsyncConnectionPool

from app.core.config import Environment, settings
from app.core.langgraph.filesystem_middleware import PreviewOnlyFilesystemMiddleware
from app.core.langgraph.tools import tools
from app.core.logging import logger
from app.schemas import Message
from app.services.llm import LLMRegistry
from app.services.memory import memory_service


SYSTEM_PROMPT = """\
You are a highly capable research and data assistant.

You have access to the following capabilities:
1. **Document database** — use `query_document_extractions` to run SQL
   SELECT queries against the `document_extractions` table (columns:
   id, document_name, page_number, raw_text, tables, metadata, created_at).
2. **Internet search** — use `duckduckgo_results_json` to search the web
   for up-to-date information.

When answering questions:
- If the user asks about documents, patient data, or anything that might
  be stored in the database, query the database first.
- If the user asks about current events, research topics, or anything
  that benefits from web search, use internet search.
- You may combine both tools when appropriate.
- Always cite your sources (document names or search results).
- Be concise but thorough.
"""

MEMORY_CONTEXT_PREFIX = """Relevant long-term memory for this session:
Use this only as supporting context when it is helpful and consistent with the latest user request.
"""

COMPACTION_SUMMARY_TEMPLATE = """Session summary from earlier conversation:
{summary}
"""

COMPACTION_SYSTEM_PROMPT = """\
Summarize the older portion of this conversation into a compact session memory.

Requirements:
- Preserve durable user preferences, constraints, and goals.
- Preserve facts, commitments, and unresolved follow-ups.
- Omit small talk and transient details.
- Keep it concise but specific.
- Return plain text only.
"""

LANGGRAPH_ROOT = Path(__file__).resolve().parent
SKILL_SOURCES = ["/skills/statute_analysis/", "/skills/canned_responses/"]


class LangGraphAgent:
    """Manages the Deep Agent workflow with DB query and internet search.

    Wraps a `create_deep_agent` compiled graph with a PostgreSQL
    checkpointer for conversation persistence.
    """

    def __init__(self):
        self._connection_pool: Optional[AsyncConnectionPool] = None
        self._graph: Optional[CompiledStateGraph] = None

        self.model = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
        self._compaction_model = LLMRegistry.get(
            settings.LONG_TERM_MEMORY_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            max_tokens=2048,
        )
        logger.info(
            "langgraph_agent_initialized — model=%s env=%s",
            settings.DEFAULT_LLM_MODEL,
            settings.ENVIRONMENT.value,
        )

    # ------------------------------------------------------------------
    # Connection pool
    # ------------------------------------------------------------------

    async def _get_connection_pool(self) -> Optional[AsyncConnectionPool]:
        if self._connection_pool is not None:
            return self._connection_pool

        try:
            connection_url = (
                "postgresql://"
                f"{quote_plus(settings.POSTGRES_USER)}:{quote_plus(settings.POSTGRES_PASSWORD)}"
                f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )
            self._connection_pool = AsyncConnectionPool(
                connection_url,
                open=False,
                max_size=settings.POSTGRES_POOL_SIZE,
                kwargs={
                    "autocommit": True,
                    "connect_timeout": 5,
                    "prepare_threshold": None,
                },
            )
            await self._connection_pool.open()
            logger.info("connection_pool_created — max_size=%s", settings.POSTGRES_POOL_SIZE)
        except Exception as exc:
            logger.error("connection_pool_creation_failed — %s", exc)
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                return None
            raise
        return self._connection_pool

    # ------------------------------------------------------------------
    # Graph creation
    # ------------------------------------------------------------------

    async def create_graph(self) -> Optional[CompiledStateGraph]:
        """Build (or return cached) the Deep Agent graph with a PG checkpointer."""
        if self._graph is not None:
            return self._graph

        try:
            pool = await self._get_connection_pool()
            checkpointer = None
            if pool:
                checkpointer = AsyncPostgresSaver(pool)
                await checkpointer.setup()

            # Prevent DeepAgents from materializing oversized tool results
            # into `large_tool_results/call_*` files inside the project tree.
            deepagents_graph.FilesystemMiddleware = PreviewOnlyFilesystemMiddleware

            self._graph = create_deep_agent(
                model=self.model,
                tools=tools,
                skills=SKILL_SOURCES,
                system_prompt=SYSTEM_PROMPT,
                checkpointer=checkpointer,
                backend=FilesystemBackend(root_dir=LANGGRAPH_ROOT, virtual_mode=True),
            )

            logger.info(
                "deep_agent_graph_created — has_checkpointer=%s",
                checkpointer is not None,
            )
        except Exception as exc:
            logger.error("graph_creation_failed — %s", exc)
            if settings.ENVIRONMENT == Environment.PRODUCTION:
                return None
            raise
        return self._graph

    def _build_config(self, session_id: str, user_id: Optional[str]) -> dict:
        return {
            "configurable": {"thread_id": session_id},
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "environment": settings.ENVIRONMENT.value,
            },
        }

    @staticmethod
    def _coerce_text_content(content: object) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            text_parts: list[str] = []
            for block in content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(str(block.get("text", "")))
            return "".join(text_parts).strip()
        return str(content).strip()

    @staticmethod
    def _truncate_tool_content(content: str, max_chars: int = 1800) -> str:
        normalized = content.strip()
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 3].rstrip() + "..."

    @staticmethod
    def _message_signature(message: Message) -> tuple[str, str]:
        return (message.role, message.content)

    def _merge_message_lists(self, base_messages: list[Message], incoming_messages: list[Message]) -> list[Message]:
        if not base_messages:
            return incoming_messages
        if not incoming_messages:
            return base_messages

        max_overlap = min(len(base_messages), len(incoming_messages))
        overlap = 0
        for size in range(max_overlap, 0, -1):
            base_suffix = [self._message_signature(message) for message in base_messages[-size:]]
            incoming_prefix = [self._message_signature(message) for message in incoming_messages[:size]]
            if base_suffix == incoming_prefix:
                overlap = size
                break

        return [*base_messages, *incoming_messages[overlap:]]

    @staticmethod
    def _latest_user_query(messages: list[Message]) -> str:
        for message in reversed(messages):
            if message.role == "user":
                return message.content.strip()
        return ""

    async def _build_memory_context_message(
        self,
        session_id: str,
        messages: list[Message],
    ) -> Message | None:
        query = self._latest_user_query(messages)
        if not query:
            return None

        memory_context = await memory_service.search(session_id=session_id, query=query)
        if not memory_context:
            return None

        return Message(
            role="system",
            content=f"{MEMORY_CONTEXT_PREFIX}\n{memory_context}",
        )

    async def _summarize_messages(self, messages: list[Message]) -> str:
        if not messages:
            return ""

        transcript = "\n".join(f"{message.role.upper()}: {message.content}" for message in messages)
        response = await self._compaction_model.ainvoke(
            [
                SystemMessage(content=COMPACTION_SYSTEM_PROMPT),
                HumanMessage(content=transcript),
            ]
        )
        summary = self._coerce_text_content(response.content)
        if len(summary) > settings.COMPACTION_MAX_SUMMARY_CHARS:
            return summary[: settings.COMPACTION_MAX_SUMMARY_CHARS].rstrip()
        return summary

    async def _maybe_compact_messages(
        self,
        session_id: str,
        messages: list[Message],
    ) -> list[Message]:
        if not settings.COMPACTION_ENABLED:
            return messages

        stored_history = await self.get_chat_history(session_id)
        use_stored_history = len(stored_history) > len(messages)
        source_messages = stored_history if use_stored_history else messages

        trigger_count = settings.COMPACTION_TRIGGER_MESSAGE_COUNT
        keep_recent = settings.COMPACTION_KEEP_RECENT_MESSAGES
        if len(source_messages) < trigger_count or len(source_messages) <= keep_recent:
            return messages

        older_messages = source_messages[:-keep_recent]
        recent_messages = source_messages[-keep_recent:]
        summary = await self._summarize_messages(older_messages)
        if not summary:
            return messages

        await memory_service.add_compaction_summary(
            session_id=session_id,
            summary=summary,
            metadata={
                "summary_message_count": len(older_messages),
                "recent_message_count": len(recent_messages),
            },
        )
        await self.clear_chat_history(session_id)

        compacted_history = [
            Message(
                role="system",
                content=COMPACTION_SUMMARY_TEMPLATE.format(summary=summary),
            ),
            *recent_messages,
        ]
        merged_messages = (
            self._merge_message_lists(compacted_history, messages)
            if use_stored_history
            else compacted_history
        )
        logger.info(
            "session_compacted",
            session_id=session_id,
            original_message_count=len(source_messages),
            compacted_message_count=len(merged_messages),
        )
        return merged_messages

    async def _prepare_input_messages(
        self,
        session_id: str,
        messages: list[Message],
    ) -> list[dict]:
        effective_messages = await self._maybe_compact_messages(session_id, messages)
        memory_context_message = await self._build_memory_context_message(session_id, messages)
        if memory_context_message is not None:
            effective_messages = [memory_context_message, *effective_messages]
        return [message.model_dump() for message in effective_messages]

    async def _store_turn_in_memory(
        self,
        session_id: str,
        request_messages: list[Message],
        assistant_content: str,
        source: str,
    ) -> None:
        if not assistant_content.strip():
            return

        latest_user_message = next((message for message in reversed(request_messages) if message.role == "user"), None)
        memory_messages: list[dict] = []
        if latest_user_message is not None:
            memory_messages.append(latest_user_message.model_dump())
        memory_messages.append({"role": "assistant", "content": assistant_content.strip()})

        await memory_service.add(
            session_id=session_id,
            messages=memory_messages,
            metadata={"source": source},
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        if self._graph is None:
            self._graph = await self.create_graph()

        config = self._build_config(session_id=session_id, user_id=user_id)
        input_messages = await self._prepare_input_messages(session_id=session_id, messages=messages)

        try:
            response = await self._graph.ainvoke(
                {"messages": input_messages},
                config=config,
            )
            response_messages = self._extract_messages(response["messages"])
            latest_assistant = next(
                (message.content for message in reversed(response_messages) if message.role == "assistant"),
                "",
            )
            await self._store_turn_in_memory(
                session_id=session_id,
                request_messages=messages,
                assistant_content=latest_assistant,
                source="chat_response",
            )
            return response_messages
        except Exception as exc:
            logger.error("get_response failed — %s", exc)
            raise

    async def get_stream_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        if self._graph is None:
            self._graph = await self.create_graph()

        config = self._build_config(session_id=session_id, user_id=user_id)
        input_messages = await self._prepare_input_messages(session_id=session_id, messages=messages)
        streamed_chunks: list[str] = []

        try:
            async for token, _ in self._graph.astream(
                {"messages": input_messages},
                config,
                stream_mode="messages",
            ):
                try:
                    chunk = self._coerce_text_content(token.content)
                    if chunk:
                        streamed_chunks.append(chunk)
                        yield chunk
                except Exception as tok_err:
                    logger.error("token processing error — %s", tok_err)
                    continue
            if streamed_chunks:
                await self._store_turn_in_memory(
                    session_id=session_id,
                    request_messages=messages,
                    assistant_content="".join(streamed_chunks),
                    source="chat_stream",
                )
        except Exception as exc:
            logger.error("stream processing error — %s", exc)
            raise

    async def get_chat_history(self, session_id: str) -> list[Message]:
        if self._graph is None:
            self._graph = await self.create_graph()

        state: StateSnapshot = await self._graph.aget_state(
            config={"configurable": {"thread_id": session_id}}
        )
        return self._extract_messages(state.values["messages"]) if state.values else []

    async def clear_chat_history(self, session_id: str) -> None:
        pool = await self._get_connection_pool()
        if pool is None:
            return
        async with pool.connection() as conn:
            for table in settings.CHECKPOINT_TABLES:
                try:
                    await conn.execute(
                        f"DELETE FROM {table} WHERE thread_id = %s",
                        (session_id,),
                    )
                    logger.info("cleared %s for session %s", table, session_id)
                except Exception as exc:
                    logger.error("error clearing %s — %s", table, exc)
                    raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_messages(messages: list[BaseMessage]) -> list[Message]:
        extracted_messages: list[Message] = []

        for raw_message in messages:
            if isinstance(raw_message, HumanMessage):
                content = LangGraphAgent._coerce_text_content(raw_message.content)
                if content:
                    extracted_messages.append(Message(role="user", content=content))
                continue

            if isinstance(raw_message, ToolMessage):
                content = LangGraphAgent._truncate_tool_content(
                    LangGraphAgent._coerce_text_content(raw_message.content)
                )
                if content:
                    tool_name = getattr(raw_message, "name", None) or "Tool"
                    extracted_messages.append(
                        Message(
                            role="tool",
                            title=f"{tool_name} result",
                            content=content,
                            metadata={
                                "event": "result",
                                "tool_name": tool_name,
                                "tool_call_id": getattr(raw_message, "tool_call_id", None),
                            },
                        )
                    )
                continue

            if isinstance(raw_message, AIMessage):
                content = LangGraphAgent._coerce_text_content(raw_message.content)
                if content:
                    extracted_messages.append(Message(role="assistant", content=content))

                for tool_call in getattr(raw_message, "tool_calls", []) or []:
                    tool_name = tool_call.get("name", "Tool")
                    tool_args = tool_call.get("args")
                    if isinstance(tool_args, dict):
                        serialized_args = ", ".join(
                            f"{key}={value!r}" for key, value in list(tool_args.items())[:6]
                        )
                    else:
                        serialized_args = str(tool_args or "")
                    invocation_summary = (
                        f"Invoked `{tool_name}`"
                        + (f" with {serialized_args}" if serialized_args else "")
                    )
                    extracted_messages.append(
                        Message(
                            role="tool",
                            title=f"Invoked {tool_name}",
                            content=LangGraphAgent._truncate_tool_content(invocation_summary, max_chars=600),
                            metadata={
                                "event": "invocation",
                                "tool_name": tool_name,
                                "tool_call_id": tool_call.get("id"),
                                "tool_args": tool_args,
                            },
                        )
                    )
                continue

            openai_msgs = convert_to_openai_messages([raw_message])
            for message in openai_msgs:
                content = LangGraphAgent._coerce_text_content(message["content"])
                if message["role"] in ("assistant", "user") and content:
                    extracted_messages.append(Message(role=message["role"], content=content))

        return extracted_messages
