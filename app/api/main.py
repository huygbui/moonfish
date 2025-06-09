from fastapi import APIRouter

from app.api.deps import APIKeyDep
from app.api.routes import health, podcasts, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(users.router, dependencies=[APIKeyDep])
api_router.include_router(podcasts.router, dependencies=[APIKeyDep])
