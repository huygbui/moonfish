from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .database import async_session
from .models import User


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_user(session: SessionDep) -> User:
    # TODO: Update to use Token instead of hardcoding
    user = await session.get(User, 1)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


UserDep = Annotated[User, Depends(get_user)]
