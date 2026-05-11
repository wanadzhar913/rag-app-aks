"""Long-term memory service using mem0 and pgvector with optional cache layer."""

from inspect import isawaitable
from typing import Any

from mem0 import AsyncMemory

from app.core.cache import (
    cache_key,
    cache_service,
)
from app.core.config import settings
from app.core.logging import logger


class MemoryService:
    """Service for managing long-term memory using mem0 and pgvector."""

    def __init__(self):
        """Initialize the memory service."""
        self._memory: AsyncMemory | None = None

    async def _get_memory(self) -> AsyncMemory:
        if self._memory is None:
            memory_instance = AsyncMemory.from_config(
                config_dict={
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "collection_name": settings.LONG_TERM_MEMORY_COLLECTION_NAME,
                            "dbname": settings.POSTGRES_DB,
                            "user": settings.POSTGRES_USER,
                            "password": settings.POSTGRES_PASSWORD,
                            "host": settings.POSTGRES_HOST,
                            "port": settings.POSTGRES_PORT,
                        },
                    },
                    "llm": {
                        "provider": "openai",
                        "config": {"model": settings.LONG_TERM_MEMORY_MODEL},
                    },
                    "embedder": {
                        "provider": "openai",
                        "config": {"model": settings.LONG_TERM_MEMORY_EMBEDDER_MODEL},
                    },
                }
            )
            self._memory = await memory_instance if isawaitable(memory_instance) else memory_instance
        return self._memory

    async def initialize(self) -> None:
        """Pre-warm the mem0 AsyncMemory instance and its pgvector connection pool.

        Call once at startup so the first search() or add() doesn't pay the
        ~130ms from_config + pgvector.list_cols() cold-init cost.
        """
        await self._get_memory()
        logger.info("memory_service_initialized")

    @staticmethod
    def _session_cache_prefix(session_id: str) -> str:
        return f"memory:{session_id}"

    @staticmethod
    def _memory_user_id(session_id: str) -> str:
        return str(session_id)

    def _memory_filters(self, session_id: str) -> dict[str, str]:
        return {"user_id": self._memory_user_id(session_id)}

    def _search_cache_key(self, session_id: str, query: str) -> str:
        return cache_key(self._session_cache_prefix(session_id), query)

    async def invalidate_session_cache(self, session_id: str | None) -> None:
        """Invalidate cached memory searches for a session."""
        if session_id is None:
            return
        await cache_service.delete_prefix(f"{self._session_cache_prefix(str(session_id))}:")

    async def search(self, session_id: str | None, query: str) -> str:
        """Search relevant memories for a session.

        Checks cache first; on miss, queries mem0 and caches the result.

        Returns formatted memory string, or empty string on failure or when
        no session_id is supplied (anonymous sessions skip long-term memory
        rather than pooling under a shared partition).
        """
        if session_id is None:
            return ""
        try:
            # Check cache first
            key = self._search_cache_key(str(session_id), query)
            cached = await cache_service.get(key)
            if cached is not None:
                logger.debug("memory_search_cache_hit", session_id=session_id)
                return cached

            memory = await self._get_memory()
            results = await memory.search(query=query, filters=self._memory_filters(str(session_id)))
            result = "\n".join([f"* {r['memory']}" for r in results["results"]])

            # Cache successful results
            if result:
                await cache_service.set(key, result)

            return result
        except Exception as e:
            logger.error("failed_to_get_relevant_memory", error=str(e), session_id=session_id, query=query)
            return ""

    async def add(self, session_id: str | None, messages: list[dict], metadata: dict | None = None) -> None:
        """Add messages to long-term memory for a session.

        No-op when ``session_id`` is ``None`` (see ``search`` for rationale).
        """
        if session_id is None:
            return
        try:
            memory = await self._get_memory()
            payload_metadata = {"session_id": str(session_id), **(metadata or {})}
            await memory.add(
                messages,
                user_id=self._memory_user_id(str(session_id)),
                metadata=payload_metadata,
            )
            await self.invalidate_session_cache(session_id)
            logger.info("long_term_memory_updated_successfully", session_id=session_id)
        except Exception as e:
            logger.exception("failed_to_update_long_term_memory", session_id=session_id, error=str(e))

    async def add_compaction_summary(
        self,
        session_id: str | None,
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Persist a compaction summary as durable session memory."""
        if session_id is None or not summary.strip():
            return

        summary_message = {
            "role": "assistant",
            "content": f"Compacted session summary:\n{summary.strip()}",
        }
        await self.add(
            session_id=session_id,
            messages=[summary_message],
            metadata={"source": "compaction", **(metadata or {})},
        )


memory_service = MemoryService()