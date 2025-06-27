from collections import deque

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from app.api.deps import SessionCurrent, UserCurrent
from app.core.storage import DeleteObject, S3Error, minio_bucket, minio_client
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
