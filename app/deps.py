from typing import Annotated, Generator

from fastapi import Depends, HTTPException
from sqlmodel import Session

from .database import engine
from .models import User


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def get_user(session: SessionDep) -> User:
    # TODO: Update to use Token instead of hardcoding
    user = session.get(User, 1)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


UserDep = Annotated[User, Depends(get_user)]
