from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import SessionCurrent
from app.core.security import create_access_token
from app.models import (
    AppleSignInRequest,
    AuthResult,
    GuestSignInRequest,
    TokenResult,
    User,
    UserResult,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/apple", response_model=AuthResult)
async def apple_sign_in(request: AppleSignInRequest, session: SessionCurrent):
    """
    Authenticate or create user via Apple Sign In

    - Creates new user if apple_id doesn't exist
    - Upgrades guest user if device matches existing guest
    - Updates user info if provided (email/name only provided on first Apple sign in)
    - Returns JWT token for subsequent authenticated requests
    """
    # First check if user exists by apple_id
    stmt = select(User).where(User.apple_id == request.apple_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # User doesn't exist - check if we should upgrade a guest or create new
        guest_user = None

        if request.device_id:
            # Check for existing guest user on this device
            stmt = select(User).where(User.device_id == request.device_id, User.apple_id.is_(None))
            result = await session.execute(stmt)
            guest_user = result.scalar_one_or_none()

        if guest_user:
            # Upgrade existing guest user
            guest_user.apple_id = request.apple_id
            guest_user.email = request.email
            guest_user.name = request.full_name
            user = guest_user
        else:
            # Create new user
            user = User(
                apple_id=request.apple_id,
                email=request.email,
                name=request.full_name,
                device_id=request.device_id,
            )
            session.add(user)

        await session.commit()
        await session.refresh(user)
    else:
        # Existing Apple user - update info if provided
        updated = False

        if request.email:
            user.email = request.email
            updated = True
        if request.full_name:
            user.name = request.full_name
            updated = True
        # Update device_id if not set and provided
        if request.device_id:
            user.device_id = request.device_id
            updated = True

        if updated:
            await session.commit()
            await session.refresh(user)

    # Create access token
    access_token = create_access_token(data={"user_id": user.id, "apple_id": user.apple_id})

    return AuthResult(
        token=TokenResult(access_token=access_token),
        user=UserResult(**user.to_dict()),
    )


@router.post("/guest", response_model=AuthResult)
async def guest_sign_in(request: GuestSignInRequest, session: SessionCurrent):
    """
    Authenticate or create guest user

    - Creates new guest user if device_id doesn't exist
    - If device_id exists but user has Apple ID, prompt for Apple Sign In
    - Returns JWT token for subsequent authenticated requests
    """
    # Check if ANY user exists for this device
    stmt = select(User).where(User.device_id == request.device_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        if user.apple_id:
            raise HTTPException(status_code=409, detail="Please sign in with Apple")

    else:
        # Create new guest user
        user = User(device_id=request.device_id)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    access_token = create_access_token(data={"user_id": user.id})
    return AuthResult(
        token=TokenResult(access_token=access_token),
        user=UserResult(**user.to_dict()),
    )
