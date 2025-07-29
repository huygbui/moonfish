from datetime import datetime, timedelta

from minio import Minio, S3Error
from minio.deleteobjects import DeleteObject

from .config import settings

minio_client = Minio(
    settings.minio_server,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=True if settings.environment != "development" else False,
)
minio_bucket = settings.minio_bucket

S3Error = S3Error
DeleteObject = DeleteObject


def get_public_url(object_name: str, updated_at: datetime | None = None) -> str | None:
    """Generate permanent public URL with versioning"""
    if settings.environment == "development":
        protocol = "http"
        base_url = f"{protocol}://{settings.minio_server}/{minio_bucket}/{object_name}"
    else:
        protocol = "https"
        # In production, the bucket matches directly to the server url
        base_url = f"{protocol}://{settings.r2_public_domain}/{object_name}"
    if updated_at:
        version = int(updated_at.timestamp())
        return f"{base_url}?v={version}"
    else:
        return base_url


def get_upload_url(object_name: str, duration: int = 1) -> str | None:
    """Generate presigned PUT URL for uploads"""
    try:
        return minio_client.presigned_put_object(
            bucket_name=minio_bucket, object_name=object_name, expires=timedelta(hours=duration)
        )
    except Exception:
        return None
