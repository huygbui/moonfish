from datetime import datetime
from typing import Literal, Optional

from pydantic import UUID4, BaseModel, EmailStr


class UserSignUpName(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserSignUp(BaseModel):
    name: Optional[UserSignUpName] = None
    email: Optional[EmailStr] = None


class AppleAuthRequest(BaseModel):
    code: str
    state: Optional[str] = None
    user: Optional[UserSignUp] = None


class TokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class User(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    balance: int
    created_at: datetime


class Podcast(BaseModel):
    id: UUID4
    user_id: int
    topic: str
    length: Literal["short", "medium", "long"]
    level: Literal["beginner", "intermediate", "advanced"]
    format: Literal["narrative", "conversational"]
    voice: Literal["male", "female"]
    instruction: Optional[str] = None

    status: Literal["pending", "active", "completed", "cancelled"]
    step: Literal["research", "compose", "voice"]
    progress: int = 0

    title: Optional[str] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    duration: Optional[int] = None

    created_at: datetime
    updated_at: datetime


class PodcastRequest(BaseModel):
    topic: str
    length: Literal["short", "medium", "long"]
    level: Literal["beginner", "intermediate", "advanced"]
    format: Literal["narrative", "conversational"]
    voice: Literal["male", "female"]
    instruction: Optional[str] = None


class PodcastResponse(BaseModel):
    id: int
    status: Literal["pending", "active", "completed", "cancelled"] = "pending"
    title: Optional[str] = None
    step: Optional[Literal["research", "compose", "voice"]] = None
    progress: int = 0
    audio_url: Optional[str] = None
    duration: Optional[int] = None
    created_at: datetime
    updated_at: datetime
