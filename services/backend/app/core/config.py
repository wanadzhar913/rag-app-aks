"""Application configuration using pydantic-settings with environment-based loading."""

import os
from enum import Enum
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENVIRONMENT = os.getenv("ENVIRONMENT", "local")


class Environment(str, Enum):
    LOCAL = "local"
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
    PROJECT_NAME: str = "RAG App"

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_LLM_MODEL: str = "gpt-5-mini"
    MAX_TOKENS: int = 4096
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
    S3_REGION: str = "us-east-1"

    CHECKPOINT_TABLES: list[str] = [
        "checkpoint_blobs",
        "checkpoint_writes",
        "checkpoints",
    ]

    LONG_TERM_MEMORY_COLLECTION_NAME: str = "rag_app_memory"
    LONG_TERM_MEMORY_MODEL: str = "gpt-5-mini"
    LONG_TERM_MEMORY_EMBEDDER_MODEL: str = "text-embedding-3-small"


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
