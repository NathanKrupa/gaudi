"""FastAPI service with a /health route."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/users")
def list_users():
    return []


@app.get("/health")
def health():
    return {"status": "ok"}
