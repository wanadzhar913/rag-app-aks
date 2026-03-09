"""S3/MinIO object storage client for downloading documents."""

import logging
import tempfile
from pathlib import Path

import boto3

from pipeline.config import settings

logger = logging.getLogger(__name__)


def _get_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
    )


def download_to_tempfile(s3_key: str) -> Path:
    """Download an S3 object to a temporary file and return its path.

    The caller is responsible for cleaning up the file.
    """
    client = _get_client()
    suffix = Path(s3_key).suffix or ".pdf"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    client.download_fileobj(settings.S3_BUCKET, s3_key, tmp)
    tmp.close()
    logger.info("downloaded s3://%s/%s → %s", settings.S3_BUCKET, s3_key, tmp.name)
    return Path(tmp.name)
