from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionCurrent
from app.models import User, UserResult

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserResult])
async def get_users(session: SessionCurrent):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return users
