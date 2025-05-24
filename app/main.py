import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from sqlmodel import Session, select

from .database import create_db_and_tables, engine
from .models import Podcast, PodcastContentResult, PodcastCreate, PodcastResult, User, UserCreate, UserResult

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
def create_user(req: UserCreate):
    user = User.model_validate(req)
    with Session(engine) as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@app.get("/users/", response_model=list[UserResult])
def get_users():
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        return users


@app.post("/podcasts/", response_model=PodcastResult)
def create_podcast(req: PodcastCreate, user_id: int):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        podcast = Podcast.model_validate(req)
        podcast.user_id = user_id
        podcast.user = user
        session.add(podcast)
        session.commit()
        session.refresh(podcast)
        return podcast


@app.get("/podcasts/", response_model=list[PodcastResult])
def get_podcasts(user_id: int):
    with Session(engine) as session:
        podcasts = session.exec(select(Podcast).where(Podcast.user_id == user_id)).all()
        return podcasts


@app.get("/podcasts/{podcast_id}", response_model=PodcastResult)
def get_podcast(podcast_id: int):
    with Session(engine) as session:
        podcast = session.get(Podcast, podcast_id)
        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")
        return podcast


@app.get("/podcasts/{podcast_id}/content", response_model=PodcastContentResult)
def get_podcast_content(podcast_id: int):
    with Session(engine) as session:
        podcast = session.get(Podcast, podcast_id)
        if not podcast:
            raise HTTPException(status_code=404, detail="Podcast not found")

        if not podcast.content:
            raise HTTPException(status_code=404, detail="Podcast content not found")

        return podcast.content
