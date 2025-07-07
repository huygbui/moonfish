import json
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


def setup_public_bucket() -> None:
    """Configure bucket for public read access"""
    if not minio_client.bucket_exists(minio_bucket):
        minio_client.make_bucket(minio_bucket)

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{minio_bucket}/*"],
            }
        ],
    }

    minio_client.set_bucket_policy(minio_bucket, json.dumps(policy))


def get_public_url(object_name: str) -> str:
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


def get_download_url(object_name: str, duration: float = 0.25) -> str | None:
    """Generate short-term presigned URL for downloads/redirects"""
    try:
        return minio_client.presigned_get_object(
            bucket_name=minio_bucket, object_name=object_name, expires=timedelta(hours=duration)
        )
    except Exception:
        return None


# def get_presigned_get_url(object_name: str, duration=48, check_exists=True) -> str | None:
#     try:
#         if check_exists:
#             minio_client.stat_object(bucket_name=minio_bucket, object_name=object_name)

#         return minio_client.presigned_get_object(
#             bucket_name=minio_bucket, object_name=object_name, expires=timedelta(hours=duration)
#         )
#     except Exception:
#         return None


# def get_presigned_put_url(object_name: str, duration=1) -> str | None:
#     try:
#         return minio_client.presigned_put_object(
#             bucket_name=minio_bucket, object_name=object_name, expires=timedelta(hours=duration)
#         )
#     except Exception:
#         return None
