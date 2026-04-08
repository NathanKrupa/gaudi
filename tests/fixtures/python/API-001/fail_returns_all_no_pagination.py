"""Fixture for API-001: FastAPI list endpoint returns .all() with no pagination."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/users")
def list_users():
    return User.objects.all()
