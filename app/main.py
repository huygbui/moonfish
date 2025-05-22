import json
import os
from contextlib import aclosing, asynccontextmanager
from dataclasses import asdict
from typing import Dict, Generator

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google import genai
from google.genai import types
from starlette.exceptions import HTTPException
from typing_extensions import Annotated, Any

from app.auth import Auth, get_auth
from app.database import DB, get_db, init_db
from app.models import (
    AppleAuthRequest,
    TokenRequest,
    TokenResponse,
    User,
)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(recreate=True)
    api_key = os.getenv("GEMINI_API_KEY")
    app.state.genai_client = genai.Client(api_key=api_key)
    yield


app = FastAPI(title="moonfish", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    db: Annotated[Generator[DB, None, None], Depends(get_db)],
    auth: Annotated[Auth, Depends(get_auth)],
) -> Dict[str, Any]:
    try:
        token = credentials.credentials
        payload = auth.verify_access_token(token)
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.select(table="users", columns=["*"], where={"id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def format_gemini_message(role: str, content: str) -> types.Content:
    assert role in ("user", "model"), f"Invalid role: {role}"
    return types.Content(role=role, parts=[types.Part.from_text(text=content)])


async def generate_stream(
    content: str,
    chat_id: int,
    client: genai.Client,
):
    with DB() as db:
        db.insert(
            table="messages",
            values={
                "content": content,
                "role": "user",
                "type": "text",
                "chat_id": chat_id,
            },
        )
        history = db.select(
            table="messages",
            columns=["id", "content", "role", "type"],
            where={"chat_id": chat_id},
        ).fetchall()
        if not history:
            raise HTTPException(status_code=404, detail="Failed to retrieve conversation")

        result = ""

        message = db.insert(
            table="messages",
            values={
                "content": result,
                "role": "model",
                "type": "text",
                "chat_id": chat_id,
            },
        ).fetchone()
        yield {
            "event": "message_start",
            "data": json.dumps(
                {
                    "id": message.id,
                    "role": message.role,
                    "content": "",
                    "chat_id": chat_id,
                }
            ),
        }

        contents = [format_gemini_message(msg.role, msg.content) for msg in history]
        generator = await client.aio.models.generate_content_stream(model="gemini-2.0-flash", contents=contents)
        async with aclosing(generator) as stream:
            async for chunk in stream:
                if chunk.text:
                    yield {
                        "event": "delta",
                        "data": json.dumps({"v": chunk.text}),
                    }
                    result += chunk.text

        yield {"event": "message_end", "data": json.dumps({"status": "success"})}

        db.update(
            table="messages",
            values={"content": result},
            where={"id": message.id},
        )


@app.get("/")
def index():
    return {"message": "Hello, World!"}


@app.get("/me")
def me(user: Annotated[Dict[str, Any], Depends(get_user)]):
    return User(**asdict(user))


@app.get("/audio")
async def get_audio():
    audio_path = "static/sound.wav"
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(audio_path, media_type="audio/wav", filename="sound.mp3")


@app.post("/auth/apple/callback", response_model=TokenResponse)
def handle_apple_callback(req: AppleAuthRequest, auth: Annotated[Auth, Depends(get_auth)]):
    # TODO: Exchange code for tokens
    # tokens = await exchange_for_tokens(req.code)
    # id_token = tokens["id_token"]

    # TODO: Verify id_token
    # decoded = await verify_id_token(id_token)
    # sub = decoded["sub"]
    # email = decoded.get("email")
    # name = {}
    apple_sub = "mock_sub"
    apple_refresh_token = "mock_refresh"
    user_id = auth.find_or_add_user("apple", apple_sub, apple_refresh_token, req.user)
    access_token = auth.create_access_token(user_id)
    refresh_token = auth.create_and_add_refresh_token(user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.post("/auth/token", response_model=TokenResponse)
def handle_token(req: TokenRequest, auth: Annotated[Auth, Depends(get_auth)]):
    user_id = auth.verify_refresh_token(req.refresh_token)
    access_token = auth.create_access_token(user_id)
    refresh_token = auth.create_and_add_refresh_token(user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
