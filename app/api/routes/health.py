from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import SessionCurrent

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def check_heath(session: SessionCurrent):
    try:
        await session.scalar(select(1))
    except Exception:
        raise HTTPException(status_code=503, detail="Database connection failed")
