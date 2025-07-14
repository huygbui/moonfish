from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionCurrent
from app.models import SubscriptionTier, SubscriptionTierResult

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("", response_model=list[SubscriptionTierResult])
async def get_all_tiers(session: SessionCurrent):
    result = await session.execute(select(SubscriptionTier))
    return result.scalars().all()


@router.get("/{tier}", response_model=SubscriptionTierResult)
async def get_tier(tier: str, session: SessionCurrent):
    stmt = select(SubscriptionTier).where(SubscriptionTier.tier == tier)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
