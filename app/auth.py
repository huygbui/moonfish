import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated, Optional

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException

from app.database import DB, get_db
from app.models import TokenResponse, UserSignUp

load_dotenv(".env")


async def exchange_for_tokens(code: str) -> TokenResponse:
    pass


async def verify_id_token(id_token: str) -> dict:
    pass


class Auth:
    def __init__(self, db: DB):
        self.db = db
        self.jwt_secret = os.getenv("JWT_SECRET")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM")

    def create_access_token(self, user_id: int, expires_delta: Optional[timedelta] = None) -> str:
        expires = datetime.now(UTC) + (expires_delta or timedelta(days=10))
        payload = {"sub": str(user_id), "exp": expires, "type": "access"}
        token = jwt.encode(payload, self.jwt_secret, self.jwt_algorithm)
        return token

    def create_and_add_refresh_token(self, user_id: int, expires_delta: Optional[timedelta] = None) -> str:
        expires = expires_delta or datetime.now(UTC) + timedelta(days=30)
        token = secrets.token_urlsafe(64)
        self.db.insert(
            table="auth_sessions",
            values={
                "user_id": user_id,
                "refresh_token": token,
                "expires_at": expires.strftime("%Y-%m-%d %H:%M:%S"),
            },
        ).fetchone()
        return token

    def verify_access_token(self, token: str) -> dict:
        return jwt.decode(token, self.jwt_secret, [self.jwt_algorithm])

    def verify_refresh_token(self, token: str) -> int:
        token = self.db.select(
            table="auth_sessions",
            columns=["user_id", "refresh_token", "expires_at"],
            where={"refresh_token": token},
            limit=1,
        ).fetchone()
        if not token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        expires_at = datetime.strptime(token.expires_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
        if expires_at < datetime.now(UTC):
            self.db.delete(table="auth_sessions", where={"id": token.id})
            raise HTTPException(
                status_code=401,
                detail="Refresh token has expired, please login again",
            )
        return token.user_id

    def find_or_add_user(
        self,
        provider: str,
        provider_user_id: str,
        refresh_token: Optional[str] = None,
        user_data: Optional[UserSignUp] = None,
    ) -> int:
        auth_account = self.db.select(
            table="auth_accounts",
            columns=["user_id"],
            where={"provider": provider, "provider_user_id": provider_user_id},
            limit=1,
        ).fetchone()
        if not auth_account:
            # fmt: off
            user = self.db.insert(
                table="users",
                values={
                    "email": user_data.email if user_data else "",
                    "first_name": user_data.name.first_name if user_data and user_data.name else "",
                    "last_name": user_data.name.last_name if user_data and user_data.name else "",
                },
            ).fetchone()
            # fmt: off
            auth_account = self.db.insert(
                table="auth_accounts",
                values={
                    "user_id": user.id,
                    "provider": provider,
                    "provider_user_id": provider_user_id,
                    "refresh_token": refresh_token,
                },
            ).fetchone()
        return auth_account.user_id


def get_auth(db: Annotated[DB, Depends(get_db)]) -> Auth:
    return Auth(db)
