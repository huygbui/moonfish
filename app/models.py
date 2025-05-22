from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


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
    id: int
    title: Optional[str] = None
    status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
