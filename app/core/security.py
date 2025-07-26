from datetime import UTC, datetime, timedelta

import jwt
from fastapi.security import APIKeyHeader, HTTPBearer

from app.models import TokenData

from .config import settings

# JWT Bearer token security
bearer_scheme = HTTPBearer()
admin_api_key_header = APIKeyHeader(name="X-Admin-Key", scheme_name="admin_api_key_header")
client_api_key_header = APIKeyHeader(name="X-Client-Key", scheme_name="client_api_key_header")


# JWT Functions
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> tuple[str, datetime]:
    """Create a new JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.jwt_expire_days)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt, expire


def verify_token(token: str) -> TokenData | None:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: int = payload.get("user_id")
        if user_id is None:
            return None

        return TokenData(user_id=user_id)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None


def verify_admin_key(api_key: str) -> bool:
    return api_key == settings.admin_api_key


def verify_client_key(api_key: str) -> bool:
    return api_key == settings.client_api_key
