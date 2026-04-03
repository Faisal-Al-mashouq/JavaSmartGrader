from fastapi import UploadFile
from settings import s3_client, settings


def public_url_for_key(key: str) -> str:
    """Public-style URL for display; path-style for MinIO, virtual-hosted for AWS."""
    base = settings.s3_endpoint_url.rstrip("/")
    return f"{base}/{settings.s3_bucket}/{key}"


async def save_file(file: UploadFile, submission_id: int) -> str:
    """Upload file and return the S3 object key (use with _get_file / public_url_for_key)."""
    if file.filename is None:
        file.filename = "upload"
    key = f"submissions/{submission_id}/{file.filename}"
    await file.seek(0)
    s3_client.upload_fileobj(file.file, settings.s3_bucket, key)
    return key


def get_file(key: str) -> bytes:
    response = s3_client.get_object(Bucket=settings.s3_bucket, Key=key)
    return response["Body"].read()
