import hashlib
import re
from datetime import datetime, timezone
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from config import settings


class StorageNotConfigured(RuntimeError):
    pass


def _client():
    if not settings.s3_configured:
        raise StorageNotConfigured("S3 credentials and bucket name are required.")
    kwargs = {
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "region_name": settings.aws_region,
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


def ensure_bucket() -> str:
    client = _client()
    bucket = settings.s3_bucket_name
    try:
        client.head_bucket(Bucket=bucket)
        return bucket
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code not in {"404", "NoSuchBucket", "NotFound"}:
            raise

    params = {"Bucket": bucket}
    if settings.aws_region and settings.aws_region != "us-east-1":
        params["CreateBucketConfiguration"] = {"LocationConstraint": settings.aws_region}
    try:
        client.create_bucket(**params)
    except ClientError as exc:
        code = str(exc.response.get("Error", {}).get("Code", ""))
        if code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
            raise
    return bucket


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name or "document.pdf").strip(".-")
    return cleaned[:180] or "document.pdf"


def upload_pdf(file_storage, run_id: UUID, user_id: UUID) -> dict:
    client = _client()
    bucket = settings.s3_bucket_name
    filename = _safe_filename(file_storage.filename)
    data = file_storage.read()
    digest = hashlib.sha256(data).hexdigest()
    now = datetime.now(timezone.utc)
    key = (
        f"{settings.s3_key_prefix}/"
        f"{now:%Y/%m/%d}/"
        f"user-{user_id}/"
        f"run-{run_id}/"
        f"{filename}"
    )
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        ContentType=file_storage.mimetype or "application/pdf",
        Metadata={
            "fastbid24-run-id": str(run_id),
            "fastbid24-user-id": str(user_id),
            "source-filename": filename,
        },
    )
    url = f"s3://{bucket}/{key}"
    return {
        "bucket": bucket,
        "key": key,
        "url": url,
        "filename": filename,
        "size": len(data),
        "sha256": digest,
    }
