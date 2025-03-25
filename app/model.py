from typing import Optional, Dict, Any
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

class TokenResponse(BaseModel):
    token: str
