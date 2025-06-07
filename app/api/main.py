from fastapi import APIRouter

from app.api.routes import podcasts, users

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(podcasts.router)
