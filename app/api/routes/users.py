from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionCurrent
from app.models import User, UserCreate, UserResult

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/users/", response_model=list[UserResult])
async def get_users(session: SessionCurrent):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return users


@router.post("/users/", response_model=UserResult)
async def create_user(req: UserCreate, session: SessionCurrent):
    user = User(**req.model_dump())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
