"""Application configuration using pydantic-settings with environment-based loading."""

import os
from enum import Enum
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENVIRONMENT = os.getenv("ENVIRONMENT", "local")


class Environment(str, Enum):
    LOCAL = "local"
    TEST = "test"
    DEVELOPMENT = "development"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{_ENVIRONMENT}"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: Environment = Environment.LOCAL
    DEBUG: bool = True
    PROJECT_NAME: str = "Malaysian Road Transport Law Agent (Backend)"
    DESCRIPTION: str = (
        "Malaysian Road Transport Law Agent is a tool that helps users to "
        "find the law related to road transport in Malaysia."
    )
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    LOG_FORMAT: str = "console"
    LOG_DIR: Path = Path("logs")

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_LLM_MODEL: str = "gpt-5-mini"
    DEFAULT_LLM_TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 32768
    MAX_LLM_CALL_RETRIES: int = 3

    POSTGRES_USER: str = "rag_app"
    POSTGRES_PASSWORD: str = "rag_app_pass"
    POSTGRES_DB: str = "rag_app_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_POOL_SIZE: int = 5

    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "documents"
    S3_REGION: str = "ap-southeast-5"

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    EMBEDDING_BATCH_SIZE: int = 20

    RATE_LIMIT_DEFAULT: str = "1000 per day,200 per hour"
    RATE_LIMIT_CHAT: str = "100 per minute"
    RATE_LIMIT_CHAT_STREAM: str = "100 per minute"
    RATE_LIMIT_MESSAGES: str = "200 per minute"
    RATE_LIMIT_LOGIN: str = "100 per minute"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    REDIS_HOST: str = ""
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 20
    CACHE_TTL_SECONDS: int = 60

    CHECKPOINT_TABLES: list[str] = [
        "checkpoint_blobs",
        "checkpoint_writes",
        "checkpoints",
    ]

    LONG_TERM_MEMORY_COLLECTION_NAME: str = "longterm_memory"
    LONG_TERM_MEMORY_MODEL: str = "gpt-4o-mini"
    LONG_TERM_MEMORY_EMBEDDER_MODEL: str = "text-embedding-3-small"
    COMPACTION_ENABLED: bool = True
    COMPACTION_TRIGGER_MESSAGE_COUNT: int = 12
    COMPACTION_KEEP_RECENT_MESSAGES: int = 4
    COMPACTION_MAX_SUMMARY_CHARS: int = 4000


settings = Settings()


def get_postgres_connection_url(driver: str = "psycopg2") -> str:
    encoded_user = quote_plus(settings.POSTGRES_USER)
    encoded_password = quote_plus(settings.POSTGRES_PASSWORD)
    return (
        f"postgresql+{driver}://{encoded_user}:{encoded_password}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )


def get_postgres_connection_kwargs() -> dict[str, str | int]:
    return {
        "dbname": settings.POSTGRES_DB,
        "user": settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
        "host": settings.POSTGRES_HOST,
        "port": settings.POSTGRES_PORT,
    }
