"""Fixture for API-002: endpoint returns dict in one branch, JSONResponse in another."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id < 0:
        return JSONResponse({"error": "bad id"}, status_code=400)
    return {"id": item_id, "name": "widget"}
