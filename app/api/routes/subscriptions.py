from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionCurrent
from app.models import SubscriptionTier, SubscriptionTierResult

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("", response_model=list[SubscriptionTierResult])
async def get_subscription_tiers(session: SessionCurrent):
    result = await session.execute(select(SubscriptionTier))
    tiers = result.scalars().all()
    return tiers
