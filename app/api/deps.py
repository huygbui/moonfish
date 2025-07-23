from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.security import bearer_scheme, verify_token
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
        raise HTTPException(status_code=404, detail="User not found")

    return user


UserCurrent = Annotated[User, Depends(get_user)]
