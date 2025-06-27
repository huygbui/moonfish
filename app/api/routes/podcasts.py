from fastapi import APIRouter

from app.api.deps import SessionCurrent, UserCurrent

router = APIRouter(prefix="/podcast", tags=["Podcasts"])


@router.post("")
def create_podcast():
    pass


@router.get("")
def get_all_podcasts(user: UserCurrent, session: SessionCurrent):
    pass


@router.get("/{podcast_id}")
def get_podcast(podcast_id: int, user: UserCurrent, session: SessionCurrent):
    pass
