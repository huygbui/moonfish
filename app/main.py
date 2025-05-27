import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from sqlmodel import select

from .deps import SessionDep, UserDep
from .models import (
    Podcast,
    PodcastContent,
    PodcastContentCreate,
    PodcastContentResult,
    PodcastCreate,
    PodcastResult,
    PodcastUpdate,
    User,
    UserCreate,
    UserResult,
)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    api_key = os.getenv("GEMINI_API_KEY")
    app.state.genai_client = genai.Client(api_key=api_key)
    yield


app = FastAPI(title="moonfish", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/users/", response_model=UserResult)
async def create_user(req: UserCreate, session: SessionDep):
    user = User.model_validate(req)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@app.get("/users/", response_model=list[UserResult])
async def get_users(session: SessionDep):
    result = await session.execute(select(User))
    users = result.scalars().all()
    return users


@app.post("/podcasts/", response_model=PodcastResult)
async def create_podcast(req: PodcastCreate, user: UserDep, session: SessionDep):
    podcast = Podcast.model_validate(req)
    podcast.user_id = user.id
    podcast.user = user
    session.add(podcast)
    await session.commit()
    await session.refresh(podcast)
    return podcast


@app.get("/podcasts/", response_model=list[PodcastResult])
async def get_podcasts(user: UserDep, session: SessionDep):
    result = await session.execute(select(Podcast).where(Podcast.user_id == user.id))
    podcasts = result.scalars().all()
    return podcasts


@app.get("/podcasts/{podcast_id}", response_model=PodcastResult)
async def get_podcast(podcast_id: int, user: UserDep, session: SessionDep):
    podcast = await session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    return podcast


@app.put("/podcasts/{podcast_id}", response_model=PodcastResult)
async def update_podcast(req: PodcastUpdate, podcast_id: int, user: UserDep, session: SessionDep):
    podcast = await session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    data = req.model_dump(exclude_unset=True, mode="json")
    podcast.sqlmodel_update(data)
    session.add(podcast)
    await session.commit()
    await session.refresh(podcast)
    return podcast


@app.get("/podcasts/{podcast_id}/content", response_model=PodcastContentResult)
async def get_podcast_content(podcast_id: int, user: UserDep, session: SessionDep):
    result = await session.execute(
        select(PodcastContent).where(PodcastContent.podcast_id == podcast_id)
    )
    content = result.scalars().one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Podcast content not found")

    return content


@app.post("/podcasts/{podcast_id}/content", response_model=PodcastContentResult)
async def create_podcast_content(
    req: PodcastContentCreate, podcast_id: int, user: UserDep, session: SessionDep
):
    podcast = await session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    content = PodcastContent(transcript=req.transcript)
    podcast.content = content
    session.add(podcast)
    await session.commit()
    await session.refresh(content)
    return content
