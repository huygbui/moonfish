from fastapi import APIRouter, HTTPException
from sqlalchemy import select, update

from app.api.deps import SessionCurrent
from app.models import SubscriptionTier, SubscriptionTierResult, SubscriptionTierUpdate

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


@router.patch("/{tier}", response_model=SubscriptionTierResult)
async def update_tier_limits(tier: str, req: SubscriptionTierUpdate, session: SessionCurrent):
    update_data = req.model_dump(exclude_unset=True, exclude_none=True)

    if not update_data:
        stmt = select(SubscriptionTier).where(SubscriptionTier.tier == tier)
        result = await session.execute(stmt)
        tier = result.scalar_one_or_none()
        if not tier:
            raise HTTPException(status_code=404, detail=f"Tier '{tier}' not found")
    else:
        stmt = (
            update(SubscriptionTier)
            .where(SubscriptionTier.tier == tier)
            .values(**update_data)
            .returning(SubscriptionTier)
        )
        result = await session.execute(stmt)
        tier = result.scalar_one_or_none()

        if not tier:
            raise HTTPException(status_code=404, detail="Podcast not found")

        await session.commit()

    return tier
