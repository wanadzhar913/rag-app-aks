"""Document extraction model."""

from typing import Any, Optional

import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field

from app.models.base import BaseModel


class DocumentExtraction(BaseModel, table=True):
    """Document extraction model for persisted OCR and embeddings."""

    __tablename__ = "document_extractions"
    __table_args__ = (
        sa.Index("idx_doc_extractions_name", "document_name"),
        sa.Index("idx_doc_extractions_metadata", "metadata", postgresql_using="gin"),
        sa.Index(
            "idx_doc_extractions_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    document_name: str = Field(sa_column=sa.Column(sa.Text, nullable=False))
    page_number: Optional[int] = Field(default=None)
    raw_text: Optional[str] = Field(default=None, sa_column=sa.Column(sa.Text, nullable=True))
    tables: Any = Field(
        default_factory=list,
        sa_column=sa.Column(JSONB, nullable=True, server_default=sa.text("'[]'::jsonb")),
    )
    extraction_metadata: Any = Field(
        default_factory=dict,
        sa_column=sa.Column("metadata", JSONB, nullable=True, server_default=sa.text("'{}'::jsonb")),
    )
    embedding: Optional[Any] = Field(default=None, sa_column=sa.Column(VECTOR(1536), nullable=True))
