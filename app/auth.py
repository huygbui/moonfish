import jwt
import time
import os

from typing import Optional, Dict
from fastapi import HTTPException, status
from dotenv import load_dotenv
from textwrap import dedent
from datetime import datetime, timedelta, UTC

from .database import query_one, insert, update
from .model import UserSignup, AuthTokenResponse

load_dotenv(".env")

async def exchange_for_tokens(code:str) -> AuthTokenResponse:
    pass

async def verify_id_token(id_token:str) -> dict:
    pass

def create_session_token(provider:str, provider_user_id:str, refresh_token:Optional[str]=None, user_data:Optional[UserSignup]=None) -> str:
    auth = query_one("SELECT user_id FROM auth_accounts WHERE auth_accounts.provider=? AND auth_accounts.provider_user_id=? ", (provider, provider_user_id,))
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
            table="auth_accounts",
            data={
                "user_id": user.id,
                "provider": provider,
                "provider_user_id": provider_user_id,
                "refresh_token": refresh_token,
            }
        )
        payload = {"user_id": auth.user_id}
        session_token = jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm='HS256')
        session = insert(
            table="auth_sessions",
            data={
                "user_id": auth.user_id,
                "token": session_token,
                "expires_at": (datetime.now(UTC) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            }
        )
    else:
        session = query_one("SELECT token, expires_at FROM auth_sessions WHERE auth_sessions.user_id=? ", (auth.user_id,))
        expires_at = datetime.strptime(session.expires_at, "%Y-%m-%d %H:%M:%S")
        if expires_at < datetime.now(UTC):
            # TODO: validate refresh token for apple
            session = update(
                table="auth_sessions",
                data={"expires_at": (datetime.now(UTC) + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")},
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
