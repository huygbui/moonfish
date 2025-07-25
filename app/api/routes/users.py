from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.api.deps import SessionCurrent, UserCurrent
from app.models import (
    Episode,
    Podcast,
    SubscriptionTier,
    UserTierUpdate,
    UserUsageResult,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/usage", response_model=UserUsageResult)
async def get_user_usage(user: UserCurrent, session: SessionCurrent) -> UserUsageResult:
    today = date.today()
    tomorrow = today + timedelta(days=1)

    stmt = select(
        select(func.count())
        .select_from(Podcast)
        .where(Podcast.user_id == user.id)
        .scalar_subquery()
        .label("podcasts"),
        select(func.count())
        .select_from(Episode)
        .where(
            Episode.user_id == user.id,
            Episode.created_at >= today,
            Episode.created_at < tomorrow,
            Episode.status != "failed",
        )
        .scalar_subquery()
        .label("daily_episodes"),
        select(func.count())
        .select_from(Episode)
        .where(
            Episode.user_id == user.id,
            Episode.created_at >= today,
            Episode.created_at < tomorrow,
            Episode.length == "long",
            Episode.status != "failed",
        )
        .scalar_subquery()
        .label("daily_extended_episodes"),
    )
    row = (await session.execute(stmt)).one()

    await session.refresh(user, attribute_names=["subscription_tier"])
    tier = user.subscription_tier

    return UserUsageResult(
        podcasts=row.podcasts or 0,
        daily_episodes=row.daily_episodes or 0,
        daily_extended_episodes=row.daily_extended_episodes or 0,
        max_podcasts=tier.max_podcasts,
        max_daily_episodes=tier.max_daily_episodes,
        max_daily_extended_episodes=tier.max_daily_extended_episodes,
    )


@router.put("/subscription")
async def update_user_subscription(req: UserTierUpdate, user: UserCurrent, session: SessionCurrent):
    stmt = select(SubscriptionTier).where(SubscriptionTier.tier == req.tier)
    result = await session.execute(stmt)
    tier = result.scalar_one()
    try:
        result = await session.execute(stmt)
        tier = result.scalar_one()
    except Exception:
        raise HTTPException(status_code=404, detail="Tier not found")

    if tier.id != user.subscription_tier_id:
        user.subscription_tier = tier
        session.add(user)
        await session.commit()
