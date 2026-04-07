"""Fixture for FAPI-ARCH-001: endpoint declares its response_model."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Order(BaseModel):
    id: int


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: int):
    return {"id": order_id}
