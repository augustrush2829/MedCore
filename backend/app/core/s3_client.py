from __future__ import annotations

from functools import lru_cache

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings


@lru_cache
def get_s3_client():
    """Cached client. boto3 pools connections internally, so one client is
    safe to share across requests/threads.

    endpoint_url set -> MinIO (or any S3-compatible target) with explicit
    credentials. endpoint_url unset -> real AWS S3, using explicit keys if
    given or falling back to boto3's standard credential chain otherwise.
    """
    settings = get_settings()
    kwargs: dict = {
        "region_name": settings.s3_region,
        "config": BotoConfig(signature_version="s3v4"),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.s3_access_key and settings.s3_secret_key:
        kwargs["aws_access_key_id"] = settings.s3_access_key
        kwargs["aws_secret_access_key"] = settings.s3_secret_key
    return boto3.client("s3", **kwargs)


def ensure_bucket_exists(*, bucket: str | None = None) -> None:
    """Create the bucket if it doesn't exist yet. Never sets a public/read
    bucket policy - S3 and MinIO buckets are private by default, and we rely
    on that default rather than touching bucket ACLs/policies at all.
    """
    settings = get_settings()
    bucket = bucket or settings.s3_bucket
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        create_kwargs: dict = {"Bucket": bucket}
        if settings.s3_region and settings.s3_region != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": settings.s3_region}
        client.create_bucket(**create_kwargs)
