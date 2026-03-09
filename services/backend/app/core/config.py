"""Application configuration using pydantic-settings with environment-based loading."""

import os
from enum import Enum

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
    OPENAI_BASE_URL: str = "https://litellm.n1-research.com"
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
