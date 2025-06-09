from contextlib import asynccontextmanager

import sentry_sdk
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings

load_dotenv()

if settings.sentry_dsn and settings.environment != "development":
    sentry_sdk.init(
        dsn=str(settings.sentry_dsn),
        environment=settings.environment,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="moonfish", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
