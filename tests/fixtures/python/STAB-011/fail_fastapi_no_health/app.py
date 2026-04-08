"""FastAPI service with routes but no health endpoint."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/users")
def list_users():
    return []


@app.get("/orders")
def list_orders():
    return []
