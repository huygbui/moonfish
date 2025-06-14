from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Security
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.security import api_key_header, verify_api_key
from app.models import User


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


SessionCurrent = Annotated[AsyncSession, Depends(get_session)]


async def get_user(session: SessionCurrent) -> User:
    # TODO: Update to use Token instead of hardcoding
    stmt = select(User).where(User.email == "user@example.com")
    result = await session.execute(stmt)
    user = result.scalars().one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


UserCurrent = Annotated[User, Depends(get_user)]


def get_api_key(key: str = Security(api_key_header)):
    if verify_api_key(key):
        return key
    else:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")


APIKeyDep = Depends(get_api_key)
