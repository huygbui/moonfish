from fastapi import APIRouter

from app.api.routes import auth, health, podcasts, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router, dependencies=[])
api_router.include_router(podcasts.router, dependencies=[])
