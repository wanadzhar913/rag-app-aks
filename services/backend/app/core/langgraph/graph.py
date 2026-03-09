"""LangGraph Agent built on Deep Agents with DB query and internet search."""

from typing import AsyncGenerator, Optional
from urllib.parse import quote_plus

from deepagents import create_deep_agent
from langchain_core.messages import BaseMessage, convert_to_openai_messages
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from psycopg_pool import AsyncConnectionPool

from app.core.config import Environment, settings
from app.core.langgraph.tools import tools
from app.core.logging import logger
from app.schemas import Message
from app.services.llm import LLMRegistry


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


class LangGraphAgent:
    """Manages the Deep Agent workflow with DB query and internet search.

    Wraps a `create_deep_agent` compiled graph with a PostgreSQL
    checkpointer for conversation persistence.
    """

    def __init__(self):
        self._connection_pool: Optional[AsyncConnectionPool] = None
        self._graph: Optional[CompiledStateGraph] = None

        self.model = LLMRegistry.get(settings.DEFAULT_LLM_MODEL)
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

            self._graph = create_deep_agent(
                model=self.model,
                tools=tools,
                system_prompt=SYSTEM_PROMPT,
                checkpointer=checkpointer,
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

        config = {
            "configurable": {"thread_id": session_id},
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "environment": settings.ENVIRONMENT.value,
            },
        }

        input_messages = [m.model_dump() for m in messages]

        try:
            response = await self._graph.ainvoke(
                {"messages": input_messages},
                config=config,
            )
            return self._extract_messages(response["messages"])
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

        config = {
            "configurable": {"thread_id": session_id},
            "metadata": {
                "user_id": user_id,
                "session_id": session_id,
                "environment": settings.ENVIRONMENT.value,
            },
        }

        input_messages = [m.model_dump() for m in messages]

        try:
            async for token, _ in self._graph.astream(
                {"messages": input_messages},
                config,
                stream_mode="messages",
            ):
                try:
                    if token.content:
                        yield token.content
                except Exception as tok_err:
                    logger.error("token processing error — %s", tok_err)
                    continue
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
        openai_msgs = convert_to_openai_messages(messages)
        return [
            Message(role=m["role"], content=str(m["content"]))
            for m in openai_msgs
            if m["role"] in ("assistant", "user") and m["content"]
        ]
