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


class ChatRequest(BaseModel):
    content: str


class ChatResponse(BaseModel):
    id: int
    role: str
    content: str
    chat_id: Optional[int] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class User(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    balance: int
    created_at: datetime


class Chat(BaseModel):
    id: int
    title: str = None
    status: str = None
    created_at: datetime
