from datetime import timedelta

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


def get_public_url(object_name: str) -> str | None:
    """Generate permanent public URL"""
    protocol = "https" if settings.environment != "development" else "http"
    return f"{protocol}://{settings.minio_server}/{minio_bucket}/{object_name}"


def get_upload_url(object_name: str, duration: int = 1) -> str | None:
    """Generate presigned PUT URL for uploads"""
    try:
        return minio_client.presigned_put_object(
            bucket_name=minio_bucket, object_name=object_name, expires=timedelta(hours=duration)
        )
    except Exception:
        return None
