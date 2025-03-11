from fastapi import FastAPI

app = FastAPI(title="moonfish")

@app.get("/")
def index():
    return {"message": "Hello, World!"}
