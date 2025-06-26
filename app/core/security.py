from datetime import UTC, datetime, timedelta

import jwt
from fastapi.security import APIKeyHeader, HTTPBearer

from app.models import TokenData

from .config import settings

# JWT Bearer token security
bearer_scheme = HTTPBearer()
api_key_header = APIKeyHeader(name=settings.api_key_header_name, auto_error=False)


# JWT Functions
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a new JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.jwt_expire_days)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_token(token: str) -> TokenData | None:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: int = payload.get("user_id")
        apple_id: str = payload.get("apple_id")

        if user_id is None or apple_id is None:
            return None

        return TokenData(user_id=user_id, apple_id=apple_id)
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None


def verify_api_key(key: str):
    return key == settings.api_key
