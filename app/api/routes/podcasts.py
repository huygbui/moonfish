from collections import deque

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload

from app.api.deps import SessionCurrent, UserCurrent
from app.core.storage import (
    DeleteObject,
    S3Error,
    get_public_url,
    get_upload_url,
    minio_bucket,
    minio_client,
)
from app.models import (
    Episode,
    EpisodeCreate,
    EpisodeResult,
    EpisodeTaskInput,
    Podcast,
    PodcastCreate,
    PodcastResult,
    PodcastUpdate,
    PodcastUpdateResult,
)
from app.worker.workflows import podcast_generation

router = APIRouter(prefix="/podcasts", tags=["Podcasts"])


@router.get("", response_model=list[PodcastResult])
async def get_podcasts(user: UserCurrent, session: SessionCurrent) -> list[PodcastResult]:
    stmt = select(Podcast).where(Podcast.user_id == user.id)
    result = await session.execute(stmt)
    podcasts = result.scalars().all()

    return [
        PodcastResult(
            **podcast.to_dict(),
            image_url=get_public_url(f"{podcast.id}/{podcast.id}.jpg"),
        )
        for podcast in podcasts
    ]


@router.post("", response_model=PodcastResult)
async def create_podcast(
    req: PodcastCreate,
    user: UserCurrent,
    session: SessionCurrent,
) -> PodcastResult:
    podcast = Podcast(**req.model_dump(), user=user)
    session.add(podcast)
    await session.commit()
    await session.refresh(podcast)

    return PodcastResult(
        **podcast.to_dict(),
        image_upload_url=get_upload_url(f"{podcast.id}/{podcast.id}.jpg"),
        image_url=get_public_url(f"{podcast.id}/{podcast.id}.jpg"),
    )


@router.get("/{podcast_id}", response_model=PodcastResult)
async def get_podcast(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    podcast = await session.get(Podcast, podcast_id)
    if not podcast or podcast.user_id != user.id:
        raise HTTPException(status_code=404, detail="Podcast not found")

    return PodcastResult(
        **podcast.to_dict(),
        image_url=get_public_url(f"{podcast_id}/{podcast_id}.jpg"),
    )


@router.patch("/{podcast_id}", response_model=PodcastUpdateResult)
async def update_podcast(
    req: PodcastUpdate, podcast_id: int, user: UserCurrent, session: SessionCurrent
) -> PodcastUpdateResult:
    update_data = req.model_dump(exclude_unset=True)

    if not update_data:
        podcast = await session.get(Podcast, podcast_id)
        if not podcast or podcast.user_id != user.id:
            raise HTTPException(status_code=404, detail="Podcast not found")
    else:
        stmt = (
            update(Podcast)
            .where(Podcast.id == podcast_id)
            .where(Podcast.user_id == user.id)
            .values(**update_data)
            .returning(Podcast)
        )
        result = await session.execute(stmt)
        podcast = result.scalar_one_or_none()

        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")

        await session.commit()

    return PodcastUpdateResult(
        **podcast.to_dict(),
        image_upload_url=get_upload_url(f"{podcast_id}/{podcast_id}.jpg"),
        image_url=get_public_url(f"{podcast_id}/{podcast_id}.jpg", check_exists=False),
    )


@router.delete("/{podcast_id}")
async def delete_podcast(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    podcast = await session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    if podcast.user_id != user.id:
        raise HTTPException(status_code=404, detail="Podcast not found")

    try:
        # List all objects with the podcast_id prefix (folder)
        objects = minio_client.list_objects(
            minio_bucket,
            prefix=f"{podcast_id}/",  # Note the trailing slash
            recursive=True,
        )

        # Collect object names for deletion
        delete_object_list = []
        for obj in objects:
            print(obj.object_name)
            delete_object_list.append(DeleteObject(obj.object_name))

        # Delete all objects if any exist
        if delete_object_list:
            deque(minio_client.remove_objects(minio_bucket, delete_object_list), maxlen=0)

    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException()
        else:
            raise HTTPException(
                status_code=500, detail="Could not delete episode files. Please try again."
            )

    await session.delete(podcast)
    await session.commit()

    return Response(status_code=204)


@router.get("/{podcast_id}/episodes", response_model=list[EpisodeResult])
async def get_podcast_episodes(
    podcast_id: int, user: UserCurrent, session: SessionCurrent
) -> list[EpisodeResult]:
    stmt = (
        select(Episode)
        .where(Episode.podcast_id == podcast_id)
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


@router.post("/{podcast_id}/episodes", response_model=EpisodeResult)
async def create_podcast_episode(
    podcast_id: int,
    req: EpisodeCreate,
    user: UserCurrent,
    session: SessionCurrent,
):
    podcast = await session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    if podcast.user_id != user.id:
        raise HTTPException(status_code=404, detail="Podcast not found")

    episode = Episode(
        **req.model_dump(),
        format=podcast.format,
        voice1=podcast.voice1,
        voice2=podcast.voice2,
        user_id=user.id,
        podcast_id=podcast_id,
    )
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
