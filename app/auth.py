import jwt
import time
import datetime
import os

from typing import Optional, Dict
from fastapi import HTTPException, status
from dotenv import load_dotenv
from textwrap import dedent

from .database import query_one, insert
from .model import UserSignup

load_dotenv(".env")

async def exchange_for_tokens(code:str) -> dict:
    pass

async def verify_id_token(id_token:str) -> dict:
    pass

def create_session_token(provider:str, sub:str, user_data:Optional[UserSignup]=None) -> str:
    auth = query_one("SELECT user_id FROM auths WHERE auths.provider=? AND auths.provider_user_id=? ", (provider, sub,))
    if not auth:
        user = insert(
            table="users",
            data={
                "email": user_data.email if user_data else "",
                "first_name": user_data.name.first_name if user_data and user_data.name else "",
                "last_name": user_data.name.last_name if user_data and user_data.name else "",
            }
        )
        auth = insert(
            table="auths",
            data={
                "user_id": user.id,
                "provider": provider,
                "provider_user_id": sub,
            }
        )
    payload = {
        "user_id": auth.user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    return jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm='HS256')

async def verify_session_token(id_token:str) -> dict:
    payload = jwt.decode(
        id_token,
        os.getenv("JWT_SECRET"),
        algorithms=["HS256"]
    )
    return payload
