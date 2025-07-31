from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import LLM, llm
from app.core.database import async_session
from app.core.security import (
    admin_api_key_header,
    bearer_scheme,
    client_api_key_header,
    verify_admin_key,
    verify_client_key,
    verify_token,
)
from app.models import User


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


SessionCurrent = Annotated[AsyncSession, Depends(get_session)]

CredentialsCurrent = Annotated[HTTPAuthorizationCredentials, Security(bearer_scheme)]


async def get_user(credentials: CredentialsCurrent, session: SessionCurrent) -> User:
    token = credentials.credentials
    token_data = verify_token(token)

    if not token_data:
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    stmt = select(User).where(User.id == token_data.user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


UserCurrent = Annotated[User, Depends(get_user)]


async def get_admin_key(api_key: Annotated[str, Security(admin_api_key_header)]) -> str:
    """Verify admin API key using FastAPI's built-in APIKeyHeader"""
    if not api_key:
        raise HTTPException(status_code=403, detail="Admin API key required in X-Admin-Key header")

    if not verify_admin_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid admin API key")

    return api_key


async def get_client_key(api_key: Annotated[str, Security(client_api_key_header)]) -> str:
    """Verify admin API key using FastAPI's built-in APIKeyHeader"""
    if not api_key:
        raise HTTPException(
            status_code=403, detail="Client API key required in X-Client-Key header"
        )

    if not verify_client_key(api_key):
        raise HTTPException(status_code=403, detail="Invalid client API key")

    return api_key


async def get_llm():
    return llm


LLMCurrent = Annotated[LLM, Depends(get_llm)]
