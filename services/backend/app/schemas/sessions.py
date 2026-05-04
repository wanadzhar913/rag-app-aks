"""Schemas for session API endpoints."""

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    name: str = Field(default="", max_length=100)


class UpdateSessionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
