from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from sqlalchemy import select, update

from app.api.deps import SessionCurrent, get_api_key
from app.models import (
    SubscriptionTier,
    SubscriptionTierResult,
    SubscriptionTierUpdate,
    User,
    UserResult,
    UserTierUpdate,
)

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(get_api_key)])


@router.get("/users", response_model=list[UserResult])
async def get_users(session: SessionCurrent):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return users


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, session: SessionCurrent):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await session.delete(user)
    await session.commit()


@router.put("/users/{user_id}/subscription")
async def update_user_subscription(user_id: int, req: UserTierUpdate, session: SessionCurrent):
    """Update any user's subscription tier"""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stmt = select(SubscriptionTier).where(SubscriptionTier.tier == req.tier)
    result = await session.execute(stmt)
    try:
        tier = result.scalar_one()
    except Exception:
        raise HTTPException(status_code=404, detail="Tier not found")

    if tier.id != user.subscription_tier_id:
        user.subscription_tier = tier
        session.add(user)
        await session.commit()


@router.get("/subscriptions", response_model=list[SubscriptionTierResult])
async def get_all_tiers(session: SessionCurrent):
    result = await session.execute(select(SubscriptionTier))
    return result.scalars().all()


@router.patch("/subscriptions/{tier}", response_model=SubscriptionTierResult)
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
