"""Shared FastAPI dependencies for v1 endpoints."""

from fastapi import Request

from app.core.langgraph.graph import LangGraphAgent
from app.services.database import DatabaseService
from app.services.rabbitmq import RabbitMQPublisher


def get_agent(request: Request) -> LangGraphAgent:
    return request.app.state.agent


def get_db(request: Request) -> DatabaseService:
    return request.app.state.db


def get_rabbitmq(request: Request) -> RabbitMQPublisher:
    return request.app.state.rabbitmq
