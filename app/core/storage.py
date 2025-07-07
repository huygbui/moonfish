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

def get_presigned_get_url(object_name: str, duration=48, check_exists=True) -> str | None:
    try:
        if check_exists:
            minio_client.stat_object(bucket_name=minio_bucket, object_name=object_name)

        return minio_client.presigned_get_object(
            bucket_name=minio_bucket, object_name=object_name, expires=timedelta(hours=duration)
        )
    except Exception:
        return None


def get_presigned_put_url(object_name: str, duration=1) -> str | None:
    try:
        return minio_client.presigned_put_object(
            bucket_name=minio_bucket, object_name=object_name, expires=timedelta(hours=duration)
        )
    except Exception:
        return None
