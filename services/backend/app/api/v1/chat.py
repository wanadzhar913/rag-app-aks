"""Chat / QA endpoints — synchronous and streaming."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.v1.dependencies import get_agent, get_db
from app.core.langgraph.graph import LangGraphAgent
from app.schemas import ChatRequest, ChatResponse, Message
from app.services.database import DatabaseService

router = APIRouter(prefix="/sessions/{session_id}", tags=["Chat & Agents"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    session_id: str,
    body: ChatRequest,
    agent: LangGraphAgent = Depends(get_agent),
    db: DatabaseService = Depends(get_db),
):
    """Send messages and get a complete response (non-streaming)."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response_messages: list[Message] = await agent.get_response(
        messages=body.messages,
        session_id=session_id,
    )
    return ChatResponse(messages=response_messages)


@router.post("/chat/stream")
async def chat_stream(
    session_id: str,
    body: ChatRequest,
    agent: LangGraphAgent = Depends(get_agent),
    db: DatabaseService = Depends(get_db),
):
    """Send messages and receive a token-by-token SSE stream."""
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def _generate():
        async for chunk in agent.get_stream_response(
            messages=body.messages,
            session_id=session_id,
        ):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")


@router.get("/history", response_model=List[Message])
async def get_history(
    session_id: str,
    agent: LangGraphAgent = Depends(get_agent),
):
    """Retrieve the full chat history for a session."""
    return await agent.get_chat_history(session_id)


@router.delete("/history", status_code=204)
async def clear_history(
    session_id: str,
    agent: LangGraphAgent = Depends(get_agent),
):
    """Clear all chat history for a session."""
    await agent.clear_chat_history(session_id)
