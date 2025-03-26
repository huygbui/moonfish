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

class AuthTokenResponse(BaseModel):
    id_token: str
    refresh_token: Optional[str] = None

class SessionTokenResponse(BaseModel):
    token: str
