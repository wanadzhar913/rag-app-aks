"""S3/MinIO object storage client for document uploads."""

import uuid
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.logging import logger


def _get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )


def ensure_bucket() -> None:
    client = _get_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=settings.S3_BUCKET)
        logger.info("created S3 bucket '%s'", settings.S3_BUCKET)


def upload_file(
    content: bytes,
    original_filename: str,
    content_type: str = "application/pdf",
    prefix: str = "uploads",
) -> str:
    """Upload bytes to S3 and return the object key."""
    client = _get_client()
    key = f"{prefix}/{uuid.uuid4().hex}_{original_filename}"
    client.put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    logger.info("uploaded %s (%d bytes) to s3://%s/%s", original_filename, len(content), settings.S3_BUCKET, key)
    return key
