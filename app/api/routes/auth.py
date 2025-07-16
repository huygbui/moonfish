from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import SessionCurrent
from app.core.security import create_access_token
from app.models import AppleSignInRequest, AuthResult, TokenResult, User, UserResult

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/apple", response_model=AuthResult)
async def apple_sign_in(request: AppleSignInRequest, session: SessionCurrent):
    """
    Authenticate or create user via Apple Sign In

    - Creates new user if apple_id doesn't exist
    - Updates user info if provided (email/name only provided on first Apple sign in)
    - Returns JWT token for subsequent authenticated requests
    """
    # Check if user exists
    stmt = select(User).where(User.apple_id == request.apple_id)
    result = await session.execute(stmt)
    user = result.scalars().one_or_none()

    if not user:
        # Create new user
        user = User(apple_id=request.apple_id, email=request.email, name=request.full_name)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Update user info if provided (Apple only provides this on first sign in)
        updated = False
        if request.email and not user.email:
            user.email = request.email
            updated = True
        if request.full_name and not user.name:
            user.name = request.full_name
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
