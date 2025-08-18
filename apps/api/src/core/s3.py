import uuid
from datetime import datetime

import boto3
from botocore.client import Config

from src.core.config import settings


region = settings.aws_region or None

_client = boto3.client(
    "s3",
    region_name=region,
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    config=Config(signature_version="s3v4"),
)


def generate_presigned_put_url(file_name: str, content_type: str, expires: int = 600, prefix: str = "uploads") -> dict:
    """Generate a presigned PUT URL for uploading to S3.

    prefix: top-level folder to place the object under (e.g., "media" or "cvs").
    """
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET not configured")
    folder = datetime.utcnow().strftime('%Y%m%d')
    key = f"{prefix}/{folder}/{uuid.uuid4()}_{file_name}"
    url = _client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
        HttpMethod="PUT",
    )
    print(f"[S3 PRESIGN] generated key={key}")
    return {"url": url, "key": key} 


def generate_presigned_put_url_at_key(key: str, content_type: str, expires: int = 600) -> dict:
    """Generate a presigned PUT URL for an exact S3 key without adding date/uuid.

    This is useful when the caller wants full control of the path, e.g., media/{job_id}/... or cvs/{job_id}/...
    """
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET not configured")
    url = _client.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=expires,
        HttpMethod="PUT",
    )
    print(f"[S3 PRESIGN:FIXED] key={key}")
    return {"url": url, "key": key}


def put_object_bytes(key: str, body: bytes, content_type: str) -> str:
    """Upload raw bytes to S3 at the given key and return an s3:// URL."""
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET not configured")
    _client.put_object(
        Bucket=settings.s3_bucket,
        Key=key,
        Body=body,
        ContentType=content_type or "application/octet-stream",
    )
    url = f"s3://{settings.s3_bucket}/{key}"
    print(f"[S3 PUT] uploaded {len(body)} bytes to {url}")
    return url


def generate_presigned_get_url(key: str, expires: int = 600) -> str:
    """Generate a presigned GET URL for downloading from S3."""
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET not configured")
    return _client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": key,
        },
        ExpiresIn=expires,
        HttpMethod="GET",
    )