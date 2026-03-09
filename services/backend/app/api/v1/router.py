"""Aggregated v1 API router."""

from fastapi import APIRouter

from app.api.v1 import chat, documents, health, sessions

v1_router = APIRouter()
v1_router.include_router(health.router)
v1_router.include_router(sessions.router)
v1_router.include_router(chat.router)
v1_router.include_router(documents.router)
