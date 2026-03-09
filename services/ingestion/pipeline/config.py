"""Ingestion pipeline configuration using pydantic-settings."""

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

    POSTGRES_USER: str = "rag_app"
    POSTGRES_PASSWORD: str = "rag_app_pass"
    POSTGRES_DB: str = "rag_app_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASS: str = "guest"
    INGESTION_QUEUE: str = "document_ingestion"

    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "documents"
    S3_REGION: str = "us-east-1"

    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://litellm.n1-research.com"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536
    EMBEDDING_BATCH_SIZE: int = 20


settings = Settings()
