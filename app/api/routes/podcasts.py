from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import SessionCurrent, UserCurrent
from app.models import Podcast, PodcastCreate, PodcastResult

router = APIRouter(prefix="/podcast", tags=["Podcasts"])


@router.post("", response_model=PodcastResult)
async def create_podcast(
    req: PodcastCreate,
    user: UserCurrent,
    session: SessionCurrent,
):
    podcast = Podcast(**req.model_dump(), user=user)
    session.add(podcast)
    await session.commit()
    await session.refresh(podcast)

    return podcast


@router.get("", response_model=list[PodcastResult])
async def get_podcasts(user: UserCurrent, session: SessionCurrent):
    stmt = select(Podcast).where(Podcast.user_id == user.id)
    result = await session.execute(stmt)
    podcasts = result.scalars().all()
    return podcasts
    # return [PodcastResult(**podcast.to_dict()) for podcast in podcasts]


@router.get("/{podcast_id}", response_model=PodcastResult)
async def get_podcast(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    podcast = await session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    if podcast.user_id != user.id:
        raise HTTPException(status_code=404, detail="Podcast not found")

    return podcast
