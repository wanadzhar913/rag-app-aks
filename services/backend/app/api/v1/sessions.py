"""Session CRUD endpoints."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.dependencies import get_db
from app.services.database import DatabaseService
from app.schemas.auth import SessionResponse

router = APIRouter(prefix="/sessions", tags=["Sessions"])


class CreateSessionRequest(BaseModel):
    name: str = Field(default="", max_length=100)


class UpdateSessionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: CreateSessionRequest = CreateSessionRequest(),
    db: DatabaseService = Depends(get_db),
):
    session_id = str(uuid.uuid4())
    session = await db.create_session(session_id=session_id, name=body.name)
    return SessionResponse(session_id=session.id, name=session.name)


@router.get("", response_model=List[SessionResponse])
async def list_sessions(db: DatabaseService = Depends(get_db)):
    sessions = await db.get_all_sessions()
    return [SessionResponse(session_id=s.id, name=s.name) for s in sessions]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: DatabaseService = Depends(get_db)):
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionResponse(session_id=session.id, name=session.name)


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    body: UpdateSessionRequest,
    db: DatabaseService = Depends(get_db),
):
    session = await db.update_session_name(session_id, body.name)
    return SessionResponse(session_id=session.id, name=session.name)


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str, db: DatabaseService = Depends(get_db)):
    deleted = await db.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
