from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import SessionCurrent, UserCurrent
from app.core.storage import S3Error, get_public_url, minio_bucket, minio_client
from app.models import (
    Episode,
    EpisodeResult,
)
from app.worker.hatchet_client import hatchet

router = APIRouter(prefix="/episodes", tags=["Episodes"])


@router.get("", response_model=list[EpisodeResult])
async def get_episodes(user: UserCurrent, session: SessionCurrent):
    stmt = select(Episode).where(Episode.user_id == user.id).options(joinedload(Episode.content))
    result = await session.execute(stmt)
    episodes = result.scalars().unique().all()
    return [
        EpisodeResult(
            **episode.to_dict(),
            title=episode.content.title if episode.content else None,
            summary=episode.content.summary if episode.content else None,
            audio_url=get_public_url(f"{episode.podcast_id}/{episode.id}.mp3"),
        )
        for episode in episodes
    ]


@router.delete("/{episode_id}")
async def delete_episode(episode_id: int, user: UserCurrent, session: SessionCurrent):
    episode = await session.get(Episode, episode_id)
    if not episode or episode.user_id != user.id:
        raise HTTPException(status_code=404, detail="Episode not found")

    try:
        minio_client.remove_object(minio_bucket, f"{episode.podcast_id}/{episode.id}.mp3")
    except S3Error as e:
        if e.code == "NoSuchKey":
            pass
        else:
            raise HTTPException(
                status_code=500, detail="Could not delete episode audio. Please try again."
            )

    await session.delete(episode)
    await session.commit()

    return Response(status_code=204)


@router.get("/{episode_id}", response_model=EpisodeResult)
async def get_episode(episode_id: int, user: UserCurrent, session: SessionCurrent):
    episode = await session.get(Episode, episode_id)

    if not episode or episode.user_id != user.id:
        raise HTTPException(status_code=404, detail="Episode not found")

    return EpisodeResult(
        **episode.to_dict(),
        title=episode.content.title if episode.content else None,
        summary=episode.content.summary if episode.content else None,
        audio_url=get_public_url(f"{episode.podcast_id}/{episode.id}.mp3"),
    )


@router.post("/{episode_id}/cancel")
async def cancel_episode(episode_id: int, user: UserCurrent, session: SessionCurrent):
    episode = await session.get(Episode, episode_id)
    if not episode or episode.user_id != user.id:
        raise HTTPException(status_code=404, detail="Episode not found")

    if episode.status == "completed":
        raise HTTPException(status_code=409, detail="Episode is already completed")
    if episode.status in ["cancelled", "failed"]:
        return Response(status_code=204)

    if episode.hatchet_run_id:
        try:
            await hatchet.runs.aio_cancel(run_id=episode.hatchet_run_id)
        except Exception:
            raise HTTPException(status_code=500, detail="Episode cancellation failed")

    episode.status = "cancelled"
    session.add(episode)
    await session.commit()

    return Response(status_code=204)
