"""Fixture for SVC-003: health/ready endpoints are exempt from versioning."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/ready")
def ready():
    return {"ready": True}
