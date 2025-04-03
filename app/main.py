import os

from typing import Dict, Optional, List, Generator
from typing_extensions import Annotated
from fastapi import FastAPI, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from contextlib import asynccontextmanager

from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.database import init_db, get_db, DB
from app.auth import Auth, get_auth
from app.models import AppleAuthRequest, TokenRequest, TokenResponse, ChatRequest, ChatResponse

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

def find_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    db: Annotated[Generator[DB, None, None], Depends(get_db)],
    auth: Annotated[Auth, Depends(get_auth)]
) -> Optional[Dict[str,str]]:
    token = credentials.credentials
    payload = auth.verify_access_token(token)
    user_id = payload.get("sub")
    user = db.select(
        table = 'users',
        columns = ['*'],
        where = {'id': user_id}
    ).fetchone()
    if user: return user
    return HTTPException(status_code=404, detail="User not found")

@app.get("/")
def index():
    return {"message": "Hello, World!"}

@app.get("/me")
async def me(user: Annotated[Dict[str,str], Depends(find_current_user)]):
    return user

@app.get("/generate")
async def generate(prompt:List[types.Content]):
    client : genai.Client = app.state.genai_client
    response = await client.aio.models.generate_content(
        model='gemini-2.0-flash-001', contents=prompt
    )
    return response.text

@app.post("/chat")
async def handle_chat(
    req:ChatRequest,
    user: Annotated[Dict[str,str], Depends(find_current_user)],
    db:Annotated[DB, Depends(get_db)]
):
    if req.conversation_id is None:
        convo = db.insert(
            table="conversations",
            values={
                "user_id": user.id,
                "title": req.message[:30] + "..." if len(req.message) > 30 else req.message,
            }
        ).fetchone()

        messages = db.insert(
            table="messages",
            values={
                "conversation_id": convo.id,
                "content": req.message,
                "role": "user",
                "type": "text",
            }
        ).fetchone()
    else:
        convo = db.select(
            table="conversations",
            columns=["id"],
            where={
                "id": req.conversation_id,
                "user_id": user.id
            }
        ).fetchone()
        if not convo: raise HTTPException(status_code=404, detail="Conversation not found")

    messages = db.select(
        table="messages",
        columns=["id", "content", "role", "type", "created_at"],
        where={"conversation_id": convo.id}
    ).fetchall()

    def _gemini_message(role:str, content:str) -> types.Content:
        if role=="user":
            return types.UserContent(parts=[types.Part.from_text(text=content)])
        elif role=="model":
            return types.ModelContent(parts=[types.Part.from_text(text=content)])
        else:
            raise ValueError(f"Invalid role: {role}")

    gemini_messages = [_gemini_message(message.role, message.content) for message in messages]
    gemini_messages.append(_gemini_message("user", req.message))

    client : genai.Client = app.state.genai_client
    response = await client.aio.models.generate_content(
        model='gemini-2.0-flash-001', contents=gemini_messages
    )
    db.insert(
        table="messages",
        values={
            "conversation_id": convo.id,
            "content": req.message,
            "role": "user",
            "type": "text",
        }
    )
    db.insert(
        table="messages",
        values={
            "conversation_id": convo.id,
            "content": response.text,
            "role": "model",
            "type": "text",
        }
    )
    return ChatResponse(conversation_id=req.conversation_id, message=response.text)

@app.post("/auth/apple/callback", response_model=TokenResponse)
def handle_apple_callback(
    req: AppleAuthRequest,
    auth: Annotated[Auth, Depends(get_auth)]
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
    user_id = auth.find_or_add_user("apple", apple_sub, apple_refresh_token, req.user)
    access_token = auth.create_access_token(user_id)
    refresh_token = auth.create_and_add_refresh_token(user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@app.post("/auth/token", response_model=TokenResponse)
def handle_token(
    req: TokenRequest,
    auth: Annotated[Auth, Depends(get_auth)]
):
    user_id = auth.verify_refresh_token(req.refresh_token)
    access_token = auth.create_access_token(user_id)
    refresh_token = auth.create_and_add_refresh_token(user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
