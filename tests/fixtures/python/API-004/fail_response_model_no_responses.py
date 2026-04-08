"""Fixture for API-004: FastAPI route declares response_model but no error responses."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    id: int
    name: str


@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int) -> Item:
    return Item(id=item_id, name="widget")
