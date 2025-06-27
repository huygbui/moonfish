from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import SessionCurrent, UserCurrent
from app.core.storage import S3Error, minio_bucket, minio_client
from app.models import (
    Episode,
    EpisodeAudio,
    EpisodeAudioResult,
    EpisodeContent,
    EpisodeContentResult,
    EpisodeCreate,
    EpisodeResult,
    EpisodeTaskInput,
    OngoingEpisodeResult,
)
from app.worker.hatchet_client import hatchet
from app.worker.workflows import podcast_generation

router = APIRouter(prefix="/episodes", tags=["Episodes"])


@router.post("", response_model=EpisodeResult)
async def create_episode(
    req: EpisodeCreate,
    user: UserCurrent,
    session: SessionCurrent,
):
    episode = Episode(**req.model_dump(), user=user)
    session.add(episode)
    await session.commit()
    await session.refresh(episode)

    try:
        task = EpisodeTaskInput.model_validate(episode.to_dict())
        _ = await podcast_generation.aio_run_no_wait(task)
    except Exception:
        episode.status = "failed"
        await session.commit()
        raise HTTPException(status_code=500, detail="Episode generation failed")

    return episode


@router.get("", response_model=list[EpisodeResult])
async def get_episodes(user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(Episode)
        .where(Episode.user_id == user.id)
        .options(
            joinedload(Episode.audio),
            joinedload(Episode.content),
        )
    )
    result = await session.execute(stmt)
    episodes = result.scalars().unique().all()
    return [
        EpisodeResult(
            **episode.to_dict(),
            title=episode.content.title if episode.content else None,
            summary=episode.content.summary if episode.content else None,
            file_name=episode.audio.file_name if episode.audio else None,
            duration=episode.audio.duration if episode.audio else None,
        )
        for episode in episodes
    ]


@router.get("/completed", response_model=list[EpisodeResult])
async def get_completed_episodes(user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(Episode)
        .where(Episode.user_id == user.id)
        .where(Episode.status.in_(["completed"]))
        .options(
            joinedload(Episode.audio),
            joinedload(Episode.content),
        )
    )
    result = await session.execute(stmt)
    episodes = result.scalars().unique().all()
    return [
        EpisodeResult(
            **episode.to_dict(),
            title=episode.content.title if episode.content else None,
            summary=episode.content.summary if episode.content else None,
            file_name=episode.audio.file_name if episode.audio else None,
            duration=episode.audio.duration if episode.audio else None,
        )
        for episode in episodes
    ]


@router.get("/ongoing", response_model=list[OngoingEpisodeResult])
async def get_ongoing_episodes(user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(Episode)
        .where(Episode.user_id == user.id)
        .where(Episode.status.in_(["pending", "active"]))
    )
    result = await session.execute(stmt)
    episodes = result.scalars().unique().all()
    return [OngoingEpisodeResult(**episode.to_dict()) for episode in episodes]


@router.delete("/{episode_id}")
async def delete_episode(episode_id: int, user: UserCurrent, session: SessionCurrent):
    episode = await session.get(Episode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    if episode.user_id != user.id:
        raise HTTPException(status_code=404, detail="Episode not found")

    try:
        minio_client.remove_object(minio_bucket, f"{episode_id}.mp3")
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
    stmt = (
        select(Episode)
        .where(Episode.id == episode_id)
        .where(Episode.user_id == user.id)
        .options(joinedload(Episode.audio), joinedload(Episode.content))
    )

    result = await session.execute(stmt)
    episode = result.unique().scalars().one_or_none()

    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    return EpisodeResult(
        **episode.to_dict(),
        title=episode.content.title if episode.content else None,
        summary=episode.content.summary if episode.content else None,
        file_name=episode.audio.file_name if episode.audio else None,
        duration=episode.audio.duration if episode.audio else None,
    )


@router.get("/{episode_id}/content", response_model=EpisodeContentResult)
async def get_episode_content(episode_id: int, user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(EpisodeContent)
        .join(EpisodeContent.episode)
        .where(EpisodeContent.episode_id == episode_id)
        .where(Episode.user_id == user.id)
    )

    result = await session.execute(stmt)
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(status_code=404, detail="Episode content not found")

    return content


@router.get("/{episode_id}/audio", response_model=EpisodeAudioResult)
async def get_episode_audio(episode_id: int, user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(EpisodeAudio)
        .join(EpisodeAudio.episode)
        .where(EpisodeAudio.episode_id == episode_id)
        .where(Episode.user_id == user.id)
    )

    result = await session.execute(stmt)
    audio = result.scalar_one_or_none()

    if not audio:
        raise HTTPException(status_code=404, detail="Episode content not found")

    try:
        _ = minio_client.stat_object(minio_bucket, audio.file_name)

        # Define expiration
        expires_duration = timedelta(hours=48)
        expires_at = datetime.now(UTC) + expires_duration

        # Generate presigned URL valid for 1 hour
        url = minio_client.presigned_get_object(
            bucket_name=minio_bucket, object_name=audio.file_name, expires=expires_duration
        )
        return EpisodeAudioResult(url=url, expires_at=expires_at)

    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Episode audio not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{episode_id}/download")
async def download_episode_audio(episode_id: int, user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(EpisodeAudio)
        .join(EpisodeAudio.episode)
        .where(EpisodeAudio.episode_id == episode_id)
        .where(Episode.user_id == user.id)
    )

    result = await session.execute(stmt)
    audio = result.scalar_one_or_none()

    if not audio:
        raise HTTPException(status_code=404, detail="Episode content not found")

    try:
        _ = minio_client.stat_object(minio_bucket, audio.file_name)

        url = minio_client.presigned_get_object(
            bucket_name=minio_bucket,
            object_name=audio.file_name,
            expires=timedelta(minutes=15),
        )

        return RedirectResponse(url=url, status_code=307)

    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Episode audio not found")
        # You can add more specific S3 error handling here if needed
        raise HTTPException(status_code=500, detail=f"Storage error: {e.code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


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
