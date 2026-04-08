"""Fixture for API-001: list endpoint paginates the queryset before returning."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/users")
def list_users(limit: int = 50, offset: int = 0):
    return User.objects.all()[offset : offset + limit]
