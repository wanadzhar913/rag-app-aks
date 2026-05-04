"""RabbitMQ consumer that triggers the document ingestion pipeline.

Listens on the ``document_ingestion`` queue for JSON messages:

    {
        "s3_key": "uploads/abc123_report.pdf",
        "original_filename": "report.pdf"
    }
"""

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime

import pika
import psycopg2

from pipeline.config import settings
from pipeline.extraction import process_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("ingestion-worker")


def connect_with_retry(max_retries: int = 10, delay: float = 3.0) -> pika.BlockingConnection:
    credentials = pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=settings.RABBITMQ_HOST,
        port=settings.RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    for attempt in range(1, max_retries + 1):
        try:
            conn = pika.BlockingConnection(params)
            logger.info("connected to RabbitMQ at %s:%s", settings.RABBITMQ_HOST, settings.RABBITMQ_PORT)
            return conn
        except pika.exceptions.AMQPConnectionError:
            logger.warning(
                "rabbitmq not ready (attempt %d/%d), retrying in %.0fs …",
                attempt, max_retries, delay,
            )
            time.sleep(delay)
    raise RuntimeError(f"could not connect to RabbitMQ after {max_retries} attempts")


def _pg_config() -> dict:
    return {
        "host": settings.POSTGRES_HOST,
        "port": settings.POSTGRES_PORT,
        "dbname": settings.POSTGRES_DB,
        "user": settings.POSTGRES_USER,
        "password": settings.POSTGRES_PASSWORD,
    }


def update_job_status(
    job_id: str,
    status: str,
    *,
    error_message: str | None = None,
    started: bool = False,
    completed: bool = False,
) -> None:
    conn = psycopg2.connect(**_pg_config())
    try:
        now = datetime.now(UTC)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE ingestion_jobs
                SET
                    status = %s,
                    error_message = %s,
                    started_at = CASE
                        WHEN %s AND started_at IS NULL THEN %s
                        ELSE started_at
                    END,
                    completed_at = CASE
                        WHEN %s THEN %s
                        ELSE completed_at
                    END
                WHERE id = %s
                """,
                (status, error_message, started, now, completed, now, job_id),
            )
        conn.commit()
    finally:
        conn.close()


def on_message(ch, method, _properties, body):
    job_id = None
    try:
        payload = json.loads(body)
        job_id = payload["job_id"]
        s3_key = payload["s3_key"]
        original_filename = payload.get("original_filename")
        logger.info(
            "received ingestion job — job_id=%s s3_key=%s original=%s",
            job_id,
            s3_key,
            original_filename,
        )

        update_job_status(job_id, "processing", started=True)
        result = process_file(s3_key, original_filename)
        update_job_status(job_id, "completed", completed=True)
        logger.info("pipeline result: %s", json.dumps(result))

        ch.basic_ack(delivery_tag=method.delivery_tag)
    except KeyError as exc:
        logger.error("malformed message, missing key %s: %s", exc, body[:200])
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as exc:
        if job_id:
            update_job_status(job_id, "failed", error_message=str(exc), completed=True)
        logger.exception("failed to process message")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    connection = connect_with_retry()
    channel = connection.channel()
    channel.queue_declare(queue=settings.INGESTION_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=settings.INGESTION_QUEUE, on_message_callback=on_message)

    logger.info("waiting for messages on queue '%s' …", settings.INGESTION_QUEUE)
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("shutting down")
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
