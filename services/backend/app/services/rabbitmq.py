"""Async RabbitMQ publisher for dispatching ingestion jobs."""

import json
from typing import Optional

import aio_pika

from app.core.config import settings
from app.core.logging import logger

QUEUE_NAME = "document_ingestion"


class RabbitMQPublisher:
    _instance: Optional["RabbitMQPublisher"] = None
    _connection: Optional[aio_pika.abc.AbstractRobustConnection] = None
    _channel: Optional[aio_pika.abc.AbstractChannel] = None

    def __new__(cls) -> "RabbitMQPublisher":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return

        url = (
            f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}"
            f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
        )
        self._connection = await aio_pika.connect_robust(url)
        self._channel = await self._connection.channel()
        logger.info("rabbitmq publisher connected to %s:%s", settings.RABBITMQ_HOST, settings.RABBITMQ_PORT)

    async def _publish(self, payload: dict) -> None:
        await self.connect()
        assert self._channel is not None

        await self._channel.declare_queue(QUEUE_NAME, durable=True)
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=QUEUE_NAME,
        )

    async def publish_file_ingestion(
        self,
        s3_key: str,
        original_filename: str,
    ) -> None:
        """Queue a single PDF (already in S3) for ingestion."""
        payload = {
            "s3_key": s3_key,
            "original_filename": original_filename,
        }
        await self._publish(payload)
        logger.info(
            "published ingestion job — s3_key=%s original=%s",
            s3_key,
            original_filename,
        )

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("rabbitmq publisher connection closed")
