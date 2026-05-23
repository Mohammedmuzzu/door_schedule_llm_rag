import os
import boto3
import tempfile
import logging
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Optional, List

from config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    S3_BUCKET_NAME,
    S3_ENDPOINT_URL
)

logger = logging.getLogger("cloud_storage")

def get_s3_client():
    """Initialize and return the boto3 S3 client based on config."""
    if not S3_BUCKET_NAME:
        return None
        
    client_args = {
        "service_name": "s3",
        "region_name": AWS_REGION,
        "aws_access_key_id": AWS_ACCESS_KEY_ID,
        "aws_secret_access_key": AWS_SECRET_ACCESS_KEY,
    }
    
    if S3_ENDPOINT_URL:
        client_args["endpoint_url"] = S3_ENDPOINT_URL
        
    try:
        return boto3.client(**client_args)
    except Exception as e:
        logger.error("Failed to initialize S3 client: %s", e)
        return None

def download_pdf_from_s3(s3_key: str, local_path: Optional[str] = None) -> Optional[str]:
    """
    Download a PDF from S3.
    If local_path is not provided, it saves to a temporary file.
    Returns the absolute path to the downloaded file.
    """
    client = get_s3_client()
    if not client:
        return None
        
    if local_path is None:
        fd, local_path = tempfile.mkstemp(suffix=".pdf")
        os.close(fd)
        
    try:
        logger.info("Downloading s3://%s/%s to %s", S3_BUCKET_NAME, s3_key, local_path)
        client.download_file(S3_BUCKET_NAME, s3_key, local_path)
        return local_path
    except ClientError as e:
        logger.error("S3 Download failed for %s: %s", s3_key, e)
        return None

def upload_file_to_s3(local_path: str, s3_key: str) -> bool:
    """
    Upload a local file to S3.
    """
    client = get_s3_client()
    if not client:
        return False
        
    if not os.path.exists(local_path):
        logger.error("Local file not found: %s", local_path)
        return False
        
    try:
        logger.info("Uploading %s to s3://%s/%s", local_path, S3_BUCKET_NAME, s3_key)
        client.upload_file(local_path, S3_BUCKET_NAME, s3_key)
        return True
    except ClientError as e:
        logger.error("S3 Upload failed for %s: %s", s3_key, e)
        return False

def list_pdfs_in_s3(prefix: str = "pdfs/") -> List[str]:
    """
    List all PDF keys in the bucket under the given prefix.
    """
    client = get_s3_client()
    if not client:
        return []
        
    pdfs = []
    try:
        paginator = client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=S3_BUCKET_NAME, Prefix=prefix)
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.lower().endswith('.pdf'):
                        pdfs.append(key)
        return pdfs
    except ClientError as e:
        logger.error("S3 List failed: %s", e)
        return []
