"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import v1_router
from app.core.cache import cache_service
from app.core.config import settings
from app.core.langgraph.graph import LangGraphAgent
from app.core.logging import logger
from app.services.database import DatabaseService
from app.services.memory import memory_service
from app.services.rabbitmq import RabbitMQPublisher
from app.services.storage import ensure_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = DatabaseService()
    logger.info("database service ready")

    await cache_service.initialize()
    logger.info("cache service ready")

    try:
        await memory_service.initialize()
        logger.info("memory service ready")
    except Exception as exc:
        logger.warning("memory service failed to initialize at startup: %s", exc)

    agent = LangGraphAgent()
    await agent.create_graph()
    app.state.agent = agent
    logger.info("langgraph agent ready")

    rmq = RabbitMQPublisher()
    try:
        await rmq.connect()
    except Exception as exc:
        logger.warning("rabbitmq publisher failed to connect at startup: %s", exc)
    app.state.rabbitmq = rmq

    try:
        ensure_bucket()
    except Exception as exc:
        logger.warning("failed to ensure S3 bucket at startup: %s", exc)

    yield

    await cache_service.close()
    await rmq.close()
    logger.info("shutting down")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router, prefix="/api/v1")
