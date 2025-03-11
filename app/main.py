import apsw

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from .database import get_conn, init_db

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
def test_db(conn: apsw.Connection = Depends(get_conn)):
    with conn:
        rows = conn.execute("SELECT * FROM tiers").fetchall()
        return {"tiers": rows}
