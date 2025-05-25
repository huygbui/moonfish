import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from sqlmodel import select

from .database import create_db_and_tables
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
    create_db_and_tables()
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
def create_user(req: UserCreate, session: SessionDep):
    user = User.model_validate(req)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@app.get("/users/", response_model=list[UserResult])
def get_users(session: SessionDep):
    users = session.exec(select(User)).all()
    return users


@app.post("/podcasts/", response_model=PodcastResult)
def create_podcast(req: PodcastCreate, user: UserDep, session: SessionDep):
    podcast = Podcast.model_validate(req)
    podcast.user_id = user.id
    podcast.user = user
    session.add(podcast)
    session.commit()
    session.refresh(podcast)
    return podcast


@app.get("/podcasts/", response_model=list[PodcastResult])
def get_podcasts(user: UserDep, session: SessionDep):
    podcasts = session.exec(select(Podcast).where(Podcast.user_id == user.id)).all()
    return podcasts


@app.get("/podcasts/{podcast_id}", response_model=PodcastResult)
def get_podcast(podcast_id: int, user: UserDep, session: SessionDep):
    podcast = session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    return podcast


@app.put("/podcasts/{podcast_id}", response_model=PodcastResult)
def update_podcast(req: PodcastUpdate, podcast_id: int, user: UserDep, session: SessionDep):
    podcast = session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    data = req.model_dump(exclude_unset=True, mode="json")
    podcast.sqlmodel_update(data)
    session.add(podcast)
    session.commit()
    session.refresh(podcast)
    return podcast


@app.get("/podcasts/{podcast_id}/content", response_model=PodcastContentResult)
def get_podcast_content(podcast_id: int, user: UserDep, session: SessionDep):
    podcast = session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")

    if not podcast.content:
        raise HTTPException(status_code=404, detail="Podcast content not found")

    return podcast.content


@app.post("/podcasts/{podcast_id}/content", response_model=PodcastContentResult)
def create_podcast_content(
    req: PodcastContentCreate, podcast_id: int, user: UserDep, session: SessionDep
):
    podcast = session.get(Podcast, podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    content = PodcastContent(transcript=req.transcript)
    podcast.content = content
    session.add(podcast)
    session.commit()
    session.refresh(content)
    return content
