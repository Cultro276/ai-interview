import uuid
from datetime import datetime
import logging

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


logger = logging.getLogger(__name__)


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
    logger.info("[S3 PRESIGN] generated key=%s", key)
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
    logger.info("[S3 PRESIGN:FIXED] key=%s", key)
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
    logger.info("[S3 PUT] uploaded %d bytes to %s", len(body), url)
    return url


def move_object(source_key: str, dest_key: str) -> str:
    """Copy S3 object to clean path. Returns new s3:// URL."""
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET not configured")
    
    try:
        # Copy object to new location
        _client.copy_object(
            Bucket=settings.s3_bucket,
            CopySource={'Bucket': settings.s3_bucket, 'Key': source_key},
            Key=dest_key
        )
        
        new_url = f"s3://{settings.s3_bucket}/{dest_key}"
        logger.info("[S3 COPY] %s -> %s", source_key, dest_key)
        
        # Try to delete original (optional - ignore if fails due to permissions)
        try:
            _client.delete_object(
                Bucket=settings.s3_bucket,
                Key=source_key
            )
            logger.info("[S3 DELETE] Cleaned up temp file: %s", source_key)
        except Exception as del_error:
            # Check if it's just a permission issue (which is expected and harmless)
            error_str = str(del_error)
            if "AccessDenied" in error_str and "s3:DeleteObject" in error_str:
                logger.debug("[S3 DELETE] Temp file cleanup skipped due to permissions (expected): %s", source_key)
            else:
                logger.warning("[S3 DELETE] Could not delete temp file %s: %s", source_key, del_error)
            # Continue anyway - we have the file in the right place
        
        return new_url
        
    except Exception as e:
        logger.error("[S3 COPY] Failed to copy %s -> %s: %s", source_key, dest_key, e)
        # Return original URL if copy fails
        return f"s3://{settings.s3_bucket}/{source_key}"


def generate_presigned_get_url(
    key: str,
    expires: int = 600,
    response_content_disposition: str | None = None,
    response_content_type: str | None = None,
) -> str:
    """Generate a presigned GET URL for downloading from S3.

    Optionally set response content headers to encourage inline rendering.
    """
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET not configured")
    params = {
        "Bucket": settings.s3_bucket,
        "Key": key,
    }
    if response_content_disposition:
        params["ResponseContentDisposition"] = response_content_disposition
    if response_content_type:
        params["ResponseContentType"] = response_content_type
    return _client.generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=expires,
        HttpMethod="GET",
    )


def object_exists(key: str) -> bool:
    if not settings.s3_bucket:
        return False
    try:
        _client.head_object(Bucket=settings.s3_bucket, Key=key)
        return True
    except Exception:
        return False


def get_object_bytes(key: str) -> tuple[bytes, str]:
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET not configured")
    obj = _client.get_object(Bucket=settings.s3_bucket, Key=key)
    body = obj["Body"].read()
    content_type = obj.get("ContentType") or "application/octet-stream"
    return body, content_type


def upsert_lifecycle_rule(prefix: str, expire_days: int) -> dict:
    """Create or update a bucket lifecycle rule for a given prefix.

    Returns the resulting lifecycle configuration dict.
    """
    if not settings.s3_bucket:
        raise RuntimeError("S3_BUCKET not configured")
    bucket = settings.s3_bucket
    rules = []
    try:
        existing = _client.get_bucket_lifecycle_configuration(Bucket=bucket)
        rules = list(existing.get("Rules", []))
    except Exception:
        rules = []

    rule_id = f"ttl-{prefix.strip('/').replace('/', '_')}"
    new_rule = {
        "ID": rule_id,
        "Status": "Enabled",
        "Filter": {"Prefix": prefix},
        "Expiration": {"Days": int(expire_days)},
    }
    found = False
    for i, r in enumerate(rules):
        if r.get("ID") == rule_id or (r.get("Filter", {}).get("Prefix") == prefix):
            rules[i] = new_rule
            found = True
            break
    if not found:
        rules.append(new_rule)
    _client.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration={"Rules": rules})
    return {"bucket": bucket, "rules": rules}