from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, query_one, query_all

app = FastAPI(title="moonfish")

@app.on_event("startup")
async def startup():
    init_db()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def index():
    return {"message": "Hello, World!"}

@app.get("/test")
def test_db():
    qry = "SELECT * FROM tiers"
    rows = query_all(qry)
    return rows
