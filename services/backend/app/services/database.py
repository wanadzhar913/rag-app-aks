"""Database service for GenAI application."""

from typing import List, Optional
from urllib.parse import quote_plus

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlmodel import (
    Session,
    SQLModel,
    create_engine,
    select,
)

from app.models.session import Session as ChatSession
from app.core.config import Environment, settings
from app.core.logging import logger


class DatabaseService:
    """Handles all GenAI database operations using SQLModel ORM."""

    _instance: Optional["DatabaseService"] = None
    _initialized: bool = False

    def __new__(cls) -> "DatabaseService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        try:
            encoded_user = quote_plus(settings.POSTGRES_USER)
            encoded_password = quote_plus(settings.POSTGRES_PASSWORD)

            connection_url = (
                f"postgresql+psycopg2://{encoded_user}:{encoded_password}"
                f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
            )

            self.engine = create_engine(
                connection_url,
                pool_pre_ping=True,
                poolclass=QueuePool,
                pool_size=settings.POSTGRES_POOL_SIZE,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
            )

            SQLModel.metadata.create_all(self.engine)
            logger.info("postgres_database_initialized")
        except SQLAlchemyError as e:
            logger.error("database_initialization_error — %s", e)
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise

    async def create_session(self, session_id: str, name: str = "") -> ChatSession:
        """Create a new chat session.

        Args:
            session_id: The ID for the new session
            name: Optional name for the session (defaults to empty string)

        Returns:
            ChatSession: The created session
        """
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, name=name)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            # logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session by ID.

        Args:
            session_id: The ID of the session to delete

        Returns:
            bool: True if deletion was successful, False if session not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                return False

            session.delete(chat_session)
            session.commit()
            # logger.info("session_deleted", session_id=session_id)
            return True

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            Optional[ChatSession]: The session if found, None otherwise
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            return chat_session

    async def get_all_sessions(self) -> List[ChatSession]:
        """Get all sessions for a user.

        Args:
            None

        Returns:
            List[ChatSession]: List of all sessions
        """
        with Session(self.engine) as session:
            statement = select(ChatSession).order_by(ChatSession.created_at)
            sessions = session.exec(statement).all()
            return sessions

    async def update_session_name(self, session_id: str, name: str) -> ChatSession:
        """Update a session's name.

        Args:
            session_id: The ID of the session to update
            name: The new name for the session

        Returns:
            ChatSession: The updated session

        Raises:
            HTTPException: If session is not found
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")

            chat_session.name = name
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            # logger.info("session_name_updated", session_id=session_id, name=name)
            return chat_session

    def get_session_maker(self):
        """Get a session maker for creating database sessions.

        Returns:
            Session: A SQLModel session maker
        """
        return Session(self.engine)

    async def health_check(self) -> bool:
        """Check database connection health.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        try:
            with Session(self.engine) as session:
                # Execute a simple query to check connection
                session.exec(select(1)).first()
                return True
        except Exception as e:
            # logger.error("database_health_check_failed", error=str(e))
            return False