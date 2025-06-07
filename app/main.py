from contextlib import asynccontextmanager
from datetime import timedelta

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import exists, select
from sqlalchemy.orm import joinedload

from .deps import APIKeyDep, SessionCurrent, UserCurrent
from .models import (
    Podcast,
    PodcastAudioResult,
    PodcastContent,
    PodcastContentResult,
    PodcastCreate,
    PodcastResult,
    PodcastTaskInput,
    User,
    UserCreate,
    UserResult,
)
from .storage import S3Error, minio_bucket, minio_client
from .workflows import podcast_generation

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="moonfish", lifespan=lifespan, dependencies=[APIKeyDep])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/users/", response_model=UserResult)
async def create_user(req: UserCreate, session: SessionCurrent):
    user = User(**req.model_dump())
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@app.get("/users/", response_model=list[UserResult])
async def get_users(session: SessionCurrent):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return users


@app.post("/podcasts/", response_model=PodcastResult)
async def create_podcast(req: PodcastCreate, user: UserCurrent, session: SessionCurrent):
    print(req.model_dump())
    podcast = Podcast(**req.model_dump(), user_id=user.id, user=user)
    session.add(podcast)
    await session.commit()
    await session.refresh(podcast)

    task = PodcastTaskInput.model_validate(podcast.to_dict())
    run_id = podcast_generation.run_no_wait(task)

    # podcast.run_id = run_id
    # session.add(podcast)
    # await session.commit()
    # await session.refresh(podcast)

    return podcast


@app.get("/podcasts/", response_model=list[PodcastResult])
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
            url=podcast.audio.url if podcast.audio else None,
            duration=podcast.audio.duration if podcast.audio else None,
        )
        for podcast in podcasts
    ]


@app.delete("/podcasts/{podcast_id}")
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


@app.get("/podcasts/{podcast_id}", response_model=PodcastResult)
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
        url=podcast.audio.url if podcast.audio else None,
        duration=podcast.audio.duration if podcast.audio else None,
    )


@app.get("/podcasts/{podcast_id}/content", response_model=PodcastContentResult)
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


@app.get("/podcasts/{podcast_id}/audio", response_model=PodcastAudioResult)
async def get_podcast_audio(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    stmt = select(exists().where(Podcast.id == podcast_id).where(Podcast.user_id == user.id))
    result = await session.execute(stmt)
    podcast_exists = result.scalars()

    if not podcast_exists:
        raise HTTPException(status_code=404, detail="Podcast not found")

    try:
        object_name = f"{podcast_id}.mp3"
        stat = minio_client.stat_object(minio_bucket, object_name)

        # Generate presigned URL valid for 1 hour
        url = minio_client.presigned_get_object(
            bucket_name=minio_bucket,
            object_name=object_name,
            expires=timedelta(hours=1),  # 1 hour expiration
        )
        return PodcastAudioResult(url=url)

    except S3Error as e:
        if e.code == "NoSuchKey":
            raise HTTPException(status_code=404, detail="Podcast audio not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
