import uuid
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
    title: Optional[str] = None
    step: Literal["research", "compose", "voice"]
    progress: int = 0
    summary: Optional[str] = None
    transcript_id: Optional[str] = None
    audio_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PodcastRequest(BaseModel):
    id: UUID4
    user_id: int
    topic: str
    length: Literal["short", "medium", "long"]
    level: Literal["beginner", "intermediate", "advanced"]
    format: Literal["narrative", "conversational"]
    voice: Literal["male", "female"]
    instruction: Optional[str] = None


class PodcastResponse(BaseModel):
    id: UUID4 = uuid.uuid4()
    status: Literal["pending", "active", "completed", "cancelled"]
    title: Optional[str] = None
    step: Literal["research", "compose", "voice"]
    progress: int = 0
    summary: Optional[str] = None
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
