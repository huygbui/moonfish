import os
from contextlib import aclosing, asynccontextmanager
from typing import Dict, Generator, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google import genai
from google.genai import types
from sse_starlette.sse import EventSourceResponse
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
    User,
)

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(recreate=False)
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
) -> Optional[User]:
    try:
        token = credentials.credentials
        payload = auth.verify_access_token(token)
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.select(table="users", columns=["*"], where={"id": user_id}).fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        balance=user.balance,
        created_at=user.created_at,
    )


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


def format_gemini_message(role: str, content: str) -> types.Content:
    assert role in ("user", "model"), f"Invalid role: {role}"
    return types.Content(role=role, parts=[types.Part.from_text(text=content)])


async def generate(
    content: str,
    chat_id: int,
    client: genai.Client,
    db: DB,
) -> ChatResponse:
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

    contents = [format_gemini_message(msg.role, msg.content) for msg in history]
    response = await client.aio.models.generate_content(model="gemini-2.0-flash", contents=contents)
    result = db.insert(
        table="messages",
        values={
            "content": response.text,
            "role": "model",
            "type": "text",
            "chat_id": chat_id,
        },
    ).fetchone()

    return ChatResponse(
        id=result.id,
        role=result.role,
        content=result.content,
        chat_id=chat_id,
    )


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
        contents = [format_gemini_message(msg.role, msg.content) for msg in history]
        generator = await client.aio.models.generate_content_stream(model="gemini-2.0-flash", contents=contents)
        async with aclosing(generator) as stream:
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
                    result += chunk.text

        db.insert(
            table="messages",
            values={
                "content": result,
                "role": "model",
                "type": "text",
                "chat_id": chat_id,
            },
        )


@app.get("/")
def index():
    return {"message": "Hello, World!"}


@app.get("/me")
def me(user: Annotated[Dict[str, str], Depends(get_user)]):
    return user


@app.get("/chat")
def get_chats(
    user: Annotated[Dict[str, str], Depends(get_user)],
    db: Annotated[DB, Depends(get_db)],
):
    chats = db.select(
        table="chats",
        columns=["id", "title", "status", "created_at"],
        where={"user_id": user.id},
    ).fetchall()
    return {"data": chats}


@app.post("/chat/", response_model=ChatResponse)
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
        content=req.content,
        chat_id=chat.id,
        client=app.state.genai_client,
        db=db,
    )


@app.post("/chat/stream")
def handle_new_chat_stream(
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

    return EventSourceResponse(
        generate_stream(
            content=req.content,
            chat_id=chat.id,
            client=app.state.genai_client,
        ),
    )


@app.get("/chat/{chat_id}")
def handle_get_chat(
    chat: Annotated[Dict[str, str], Depends(get_chat)],
    db: Annotated[DB, Depends(get_db)],
):
    messages = db.select(
        table="messages",
        columns=["id", "content", "role"],
        where={"chat_id": chat.id},
    ).fetchall()
    return {"data": messages}


@app.delete("/chat/{chat_id}")
def handle_delete_chat(
    chat: Annotated[Dict[str, str], Depends(get_chat)],
    db: Annotated[DB, Depends(get_db)],
):
    return db.delete(
        table="chats",
        where={"id": chat.id},
    ).fetchone()


@app.post("/chat/{chat_id}", response_model=ChatResponse)
async def handle_chat(
    req: ChatRequest,
    chat: Annotated[Dict[str, str], Depends(get_chat)],
    db: Annotated[DB, Depends(get_db)],
):
    return await generate(
        content=req.content,
        chat_id=chat.id,
        client=app.state.genai_client,
        db=db,
    )


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
