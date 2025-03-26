import jwt
import time
import datetime
import os

from typing import Optional, Dict
from fastapi import HTTPException, status
from dotenv import load_dotenv
from textwrap import dedent

from .database import query_one, insert, update
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
        payload={ "user_id": auth.user_id, }
        print(datetime.datetime.utcnow() + datetime.timedelta(hours=24))
        session_token=jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm='HS256')
        session=insert(
            table="sessions",
            data={
                "user_id": auth.user_id,
                "token": session_token,
                "expires_at": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            }
        )
    else:
        now = datetime.datetime.utcnow()
        session = query_one("SELECT token, expires_at FROM sessions WHERE sessions.user_id=? ", (auth.user_id,))
        if session.expires_at < now:
            exp = now + datetime.timedelta(hours=24)
            session = update(
                table="sessions",
                data={
                    "expires_at": exp,
                    "updated_at": now
                },
                where="id=?",
                values=(session.id,)
            )
    return session.token

async def verify_session_token(token:str) -> dict:
    payload = jwt.decode(
        token,
        os.getenv("JWT_SECRET"),
        algorithms=["HS256"]
    )
    return payload
