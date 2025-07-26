from fastapi import APIRouter
from fastapi.param_functions import Depends
from sqlalchemy import select

from app.api.deps import SessionCurrent, get_client_key
from app.core.security import create_access_token
from app.models import (
    AuthResult,
    GuestSignInRequest,
    TokenResult,
    User,
    UserResult,
)

router = APIRouter(prefix="/auth", tags=["Authentication"], dependencies=[Depends(get_client_key)])


@router.post("/guest", response_model=AuthResult)
async def guest_sign_in(request: GuestSignInRequest, session: SessionCurrent):
    """
    Authenticate or create guest user

    - Creates new guest user if device_id doesn't exist
    - Returns JWT token for subsequent authenticated requests
    """
    # Check if ANY user exists for this device
    stmt = select(User).where(User.device_id == request.device_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Create new guest user
        user = User(device_id=request.device_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    access_token, expires_at = create_access_token(data={"user_id": user.id})
    return AuthResult(
        token=TokenResult(access_token=access_token, expires_at=int(expires_at.timestamp())),
        user=UserResult(**user.to_dict()),
    )
