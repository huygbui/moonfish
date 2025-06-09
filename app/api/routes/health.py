from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import SessionCurrent

router = APIRouter(tags=["Health"])


@router.get("/health")
async def check_heath(session: SessionCurrent):
    try:
        await session.scalar(select(1))
    except Exception:
        raise HTTPException(status_code=503, detail="Database connection failed")
