"""Fixture for API-002: endpoint returns the same dict shape in every branch."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/items/{item_id}")
def get_item(item_id: int):
    if item_id < 0:
        return {"error": "bad id"}
    return {"id": item_id, "name": "widget"}
