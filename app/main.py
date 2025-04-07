import os
from contextlib import asynccontextmanager
from typing import Dict, Generator, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google import genai
from google.genai import types
from starlette.exceptions import HTTPException
from typing_extensions import Annotated

from app.auth import Auth, get_auth
from app.database import DB, get_db, init_db
from app.models import (
    AppleAuthRequest,
    ChatRequest,
    ChatResponse,
    TokenRequest,
    TokenResponse,
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
) -> Optional[Dict[str, str]]:
    try:
        token = credentials.credentials
        payload = auth.verify_access_token(token)
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.select(
        table="users", columns=["*"], where={"id": user_id}
    ).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_chat(
    chat_id: int,
    user: Annotated[Dict[str, str], Depends(get_user)],
    db: Annotated[DB, Depends(get_db)],
):
    chat = db.select(
        table="chats",
        columns=["id", "user_id"],
        where={"id": chat_id, "user_id": user.id},
    ).fetchone()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return chat


async def generate(
    chat_id: int,
    content: str,
    client: genai.Client,
    db: DB,
) -> ChatResponse:
    db.insert(
        table="messages",
        values={
            "chat_id": chat_id,
            "content": content,
            "role": "user",
            "type": "text",
        },
    )

    history = db.select(
        table="messages",
        columns=["id", "content", "role", "type", "created_at"],
        where={"chat_id": chat_id},
    ).fetchall()
    if not history:
        raise HTTPException(
            status_code=404, detail="Failed to retrieve conversation"
        )

    def _gemini_content(role: str, content: str) -> types.Content:
        assert role in ("user", "model"), f"Invalid role: {role}"
        return types.Content(
            role=role, parts=[types.Part.from_text(text=content)]
        )

    contents = [_gemini_content(msg.role, msg.content) for msg in history]

    response = await client.aio.models.generate_content(
        model="gemini-2.0-flash-001", contents=contents
    )
    result = db.insert(
        table="messages",
        values={
            "chat_id": chat_id,
            "content": response.text,
            "role": "model",
            "type": "text",
        },
    ).fetchone()

    return ChatResponse(
        chat_id=result.chat_id,
        content=result.content,
        created_at=result.created_at,
    )


@app.get("/")
def index():
    return {"message": "Hello, World!"}


@app.get("/me")
async def me(user: Annotated[Dict[str, str], Depends(get_user)]):
    return user


@app.get("/chat")
async def get_chats(
    user: Annotated[Dict[str, str], Depends(get_user)],
    db: Annotated[DB, Depends(get_db)],
):
    chats = db.select(
        table="chats",
        columns=["id", "title", "status", "credits_used"],
        where={"user_id": user.id},
    ).fetchall()
    return chats


@app.post("/chat", response_model=ChatResponse)
async def handle_new_chat(
    req: ChatRequest,
    user: Annotated[Dict[str, str], Depends(get_user)],
    db: Annotated[DB, Depends(get_db)],
):
    chat = db.insert(
        table="chats",
        values={
            "user_id": user.id,
        },
    ).fetchone()
    if not chat:
        raise HTTPException(status_code=400, detail="Failed to create chat")

    return await generate(
        chat_id=chat.id,
        content=req.content,
        client=app.state.genai_client,
        db=db,
    )


@app.get("/chat/{chat_id}")
async def get_messages(
    chat: Annotated[Dict[str, str], Depends(get_chat)],
    db: Annotated[DB, Depends(get_db)],
):
    return db.select(
        table="messages",
        columns=["id", "content", "role", "created_at"],
        where={"chat_id": chat.id},
    ).fetchall()


@app.post("/chat/{chat_id}", response_model=ChatResponse)
async def handle_chat(
    req: ChatRequest,
    chat: Annotated[Dict[str, str], Depends(get_chat)],
    db: Annotated[DB, Depends(get_db)],
):
    return await generate(
        chat_id=chat.id,
        content=req.content,
        client=app.state.genai_client,
        db=db,
    )


@app.post("/auth/apple/callback", response_model=TokenResponse)
def handle_apple_callback(
    req: AppleAuthRequest, auth: Annotated[Auth, Depends(get_auth)]
):
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
    user_id = auth.find_or_add_user(
        "apple", apple_sub, apple_refresh_token, req.user
    )
    access_token = auth.create_access_token(user_id)
    refresh_token = auth.create_and_add_refresh_token(user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@app.post("/auth/token", response_model=TokenResponse)
def handle_token(req: TokenRequest, auth: Annotated[Auth, Depends(get_auth)]):
    user_id = auth.verify_refresh_token(req.refresh_token)
    access_token = auth.create_access_token(user_id)
    refresh_token = auth.create_and_add_refresh_token(user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
