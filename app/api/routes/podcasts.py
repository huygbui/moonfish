from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import SessionCurrent, UserCurrent
from app.core.storage import S3Error, minio_bucket, minio_client
from app.models import (
    OngoingPodcastResult,
    Podcast,
    PodcastAudio,
    PodcastAudioResult,
    PodcastContent,
    PodcastContentResult,
    PodcastCreate,
    PodcastResult,
    PodcastTaskInput,
)
from app.worker.hatchet_client import hatchet
from app.worker.workflows import podcast_generation

router = APIRouter(prefix="/podcasts", tags=["Podcasts"])


@router.post("", response_model=PodcastResult)
async def create_podcast(
    req: PodcastCreate,
    user: UserCurrent,
    session: SessionCurrent,
):
    try:
        podcast = Podcast(**req.model_dump(), user=user)
        session.add(podcast)
        await session.flush()

        task = PodcastTaskInput.model_validate(podcast.to_dict())
        run_ref = await podcast_generation.aio_run_no_wait(task)
        podcast.hatchet_run_id = run_ref.workflow_run_id

        await session.commit()
        await session.refresh(podcast)

        return podcast
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=500, detail="Podcast creation failed")


@router.get("", response_model=list[PodcastResult])
async def get_podcasts(user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(Podcast)
        .where(Podcast.user_id == user.id)
        .options(
            joinedload(Podcast.audio),
            joinedload(Podcast.content),
        )
    )
    result = await session.execute(stmt)
    podcasts = result.scalars().unique().all()
    return [
        PodcastResult(
            **podcast.to_dict(),
            title=podcast.content.title if podcast.content else None,
            summary=podcast.content.summary if podcast.content else None,
            file_name=podcast.audio.file_name if podcast.audio else None,
            duration=podcast.audio.duration if podcast.audio else None,
        )
        for podcast in podcasts
    ]


@router.get("/completed", response_model=list[PodcastResult])
async def get_completed_podcasts(user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(Podcast)
        .where(Podcast.user_id == user.id)
        .where(Podcast.status.in_(["completed"]))
        .options(
            joinedload(Podcast.audio),
            joinedload(Podcast.content),
        )
    )
    result = await session.execute(stmt)
    podcasts = result.scalars().unique().all()
    return [
        PodcastResult(
            **podcast.to_dict(),
            title=podcast.content.title if podcast.content else None,
            summary=podcast.content.summary if podcast.content else None,
            file_name=podcast.audio.file_name if podcast.audio else None,
            duration=podcast.audio.duration if podcast.audio else None,
        )
        for podcast in podcasts
    ]


@router.get("/ongoing", response_model=list[OngoingPodcastResult])
async def get_ongoing_podcasts(user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(Podcast)
        .where(Podcast.user_id == user.id)
        .where(Podcast.status.in_(["pending", "active"]))
    )
    result = await session.execute(stmt)
    podcasts = result.scalars().unique().all()
    return [OngoingPodcastResult(**podcast.to_dict()) for podcast in podcasts]


@router.delete("/{podcast_id}")
async def delete_podcast(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    podcast = await session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    if podcast.user_id != user.id:
        raise HTTPException(status_code=404, detail="Podcast not found")

    try:
        minio_client.remove_object(minio_bucket, f"{podcast_id}.mp3")
    except S3Error as e:
        if e.code == "NoSuchKey":
            pass
        else:
            raise HTTPException(
                status_code=500, detail="Could not delete podcast audio. Please try again."
            )

    await session.delete(podcast)
    await session.commit()

    return Response(status_code=204)


@router.get("/{podcast_id}", response_model=PodcastResult)
async def get_podcast(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(Podcast)
        .where(Podcast.id == podcast_id)
        .where(Podcast.user_id == user.id)
        .options(joinedload(Podcast.audio), joinedload(Podcast.content))
    )

    result = await session.execute(stmt)
    podcast = result.unique().scalars().one_or_none()

    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    return PodcastResult(
        **podcast.to_dict(),
        title=podcast.content.title if podcast.content else None,
        summary=podcast.content.summary if podcast.content else None,
        file_name=podcast.audio.file_name if podcast.audio else None,
        duration=podcast.audio.duration if podcast.audio else None,
    )


@router.get("/{podcast_id}/content", response_model=PodcastContentResult)
async def get_podcast_content(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(PodcastContent)
        .join(PodcastContent.podcast)
        .where(PodcastContent.podcast_id == podcast_id)
        .where(Podcast.user_id == user.id)
    )

    result = await session.execute(stmt)
    content = result.scalar_one_or_none()

    if not content:
        raise HTTPException(status_code=404, detail="Podcast content not found")

    return content


@router.get("/{podcast_id}/audio", response_model=PodcastAudioResult)
async def get_podcast_audio(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    stmt = (
        select(PodcastAudio)
        .join(PodcastAudio.podcast)
        .where(PodcastAudio.podcast_id == podcast_id)
        .where(Podcast.user_id == user.id)
    )

    result = await session.execute(stmt)
    audio = result.scalar_one_or_none()

    if not audio:
        raise HTTPException(status_code=404, detail="Podcast content not found")

    try:
        _ = minio_client.stat_object(minio_bucket, audio.file_name)

        # Define expiration
        expires_duration = timedelta(hours=48)
        expires_at = datetime.now(UTC) + expires_duration

        # Generate presigned URL valid for 1 hour
        url = minio_client.presigned_get_object(
            bucket_name=minio_bucket, object_name=audio.file_name, expires=expires_duration
        )
        return PodcastAudioResult(url=url, expires_at=expires_at)

    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Podcast audio not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{podcast_id}/cancel")
async def cancel_podcast(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    podcast = await session.get(Podcast, podcast_id)
    if not podcast or podcast.user_id != user.id:
        raise HTTPException(status_code=404, detail="Podcast not found")

    if podcast.status == "completed":
        raise HTTPException(status_code=409, detail="Podcast is already completed")
    if podcast.status in ["cancelled", "failed"]:
        return Response(status_code=204)

    if podcast.hatchet_run_id:
        try:
            await hatchet.runs.aio_cancel(run_id=podcast.hatchet_run_id)
        except Exception:
            raise HTTPException(status_code=500, detail="Podcast cancellation failed")

    podcast.status = "cancelled"
    session.add(podcast)
    await session.commit()

    return Response(status_code=204)
