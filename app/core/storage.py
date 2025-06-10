from minio import Minio, S3Error

from .config import settings

minio_client = Minio(
    settings.minio_server,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=True if settings.environment != "development" else False,
)
minio_bucket = settings.minio_bucket

S3Error = S3Error
