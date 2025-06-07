from fastapi.security import APIKeyHeader

from .config import settings

api_key_header = APIKeyHeader(name=settings.api_key_header_name, auto_error=False)


def verify_api_key(key: str):
    return key == settings.api_key
