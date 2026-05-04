"""Schemas for document API endpoints."""

from typing import Any, Optional

from pydantic import BaseModel, Field


class DocumentExtractionResponse(BaseModel):
    id: int
    document_name: str
    page_number: Optional[int] = None
    raw_text: Optional[str] = None
    tables: Any = Field(default_factory=list)
    metadata: Any = Field(default_factory=dict)
    created_at: Optional[str] = None


class DocumentSummary(BaseModel):
    document_name: str
    total_pages: int
    total_rows: int
    has_tables: bool
    report_date: Optional[str] = None
    created_at: Optional[str] = None


class PaginatedResponse(BaseModel):
    items: list[DocumentExtractionResponse]
    total: int
    limit: int
    offset: int


class IngestionJobResponse(BaseModel):
    id: str
    s3_key: str
    original_filename: str
    status: str
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
