from minio import Minio, S3Error
from .config import settings

minio_client = Minio(
    f"{settings.minio_server}:{settings.minio_port}",
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=False,
)
minio_bucket = settings.minio_bucket
