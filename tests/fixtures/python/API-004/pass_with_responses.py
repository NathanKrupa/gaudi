"""Fixture for API-004: FastAPI route documents both response_model and errors."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    id: int
    name: str


class Error(BaseModel):
    detail: str


@app.get(
    "/items/{item_id}",
    response_model=Item,
    responses={404: {"model": Error}, 400: {"model": Error}},
)
def get_item(item_id: int) -> Item:
    return Item(id=item_id, name="widget")
