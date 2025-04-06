from typing import Optional
from pydantic import BaseModel, EmailStr

class UserSignupName(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserSignup(BaseModel):
    name: Optional[UserSignupName] = None
    email: Optional[EmailStr] = None

class AppleAuthRequest(BaseModel):
    code: str
    state: Optional[str] = None
    user: Optional[UserSignup] = None

class TokenRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'

class ChatRequest(BaseModel):
    content:str

class ChatResponse(BaseModel):
    chat_id: Optional[int] = None
    content: str

class ChatMessage(BaseModel):
    role:str
    content:str
