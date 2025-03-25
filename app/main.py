from typing import Dict, Optional
from fastapi import FastAPI, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException

from .database import init_db, query_one
from .model import AppleAuthRequest, TokenResponse
from .auth import exchange_for_tokens, verify_session_token, create_session_token

app = FastAPI(title="moonfish")

@app.on_event("startup")
async def startup():
    init_db(replace=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> Optional[Dict[str,str]]:
    token = credentials.credentials
    payload = await verify_session_token(token)
    user_id = payload.get("user_id")
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user: return user
    raise ValueError("User not found")

@app.get("/")
def index():
    return {"message": "Hello, World!"}

@app.get("/me")
def me(user: Dict[str,str] = Depends(get_current_user)):
    return user

@app.post("/auth/apple", response_model=TokenResponse)
async def handle_apple_auth(req: AppleAuthRequest):
    try:
        # TODO: Exchange code for tokens
        # tokens = await exchange_for_tokens(req.code)
        # id_token = tokens["id_token"]

        # TODO: Verify id_token
        # decoded = await verify_id_token(id_token)
        # sub = decoded["sub"]
        # email = decoded.get("email")
        # name = {}
        sub = "mock_sub"
        session_token = create_session_token("apple", sub, req.user)
        return TokenResponse(token=session_token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Something went wrong: {e}")
