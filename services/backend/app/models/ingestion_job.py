"""Ingestion job model."""

from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Field

from app.models.base import BaseModel


class IngestionJob(BaseModel, table=True):
    """Track asynchronous document ingestion jobs."""

    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        sa.Index("idx_ingestion_jobs_status", "status"),
    )

    id: str = Field(primary_key=True, max_length=255)
    s3_key: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    original_filename: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    status: str = Field(default="queued", max_length=32)
    error_message: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text, nullable=True))
    started_at: Optional[datetime] = Field(default=None, nullable=True)
    completed_at: Optional[datetime] = Field(default=None, nullable=True)
