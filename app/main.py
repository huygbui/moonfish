import os

from typing import Dict, Optional, List, Generator
from typing_extensions import Annotated
from fastapi import FastAPI, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from contextlib import asynccontextmanager

from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.database import init_db, get_db, DB
from app.auth import Auth, get_auth
from app.models import AppleAuthRequest, TokenRequest, TokenResponse

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

@app.post("/auth/apple", response_model=TokenResponse)
def handle_apple_auth(
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
def handle_refresh_token(
    req: TokenRequest,
    auth: Annotated[Auth, Depends(get_auth)]
):
    user_id = auth.verify_refresh_token(req.refresh_token)
    access_token = auth.create_access_token(user_id)
    refresh_token = auth.create_and_add_refresh_token(user_id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)
