"""Fixture for SVC-003: route includes a /v1/ version prefix."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/v1/orders/{order_id}")
def get_order(order_id: int):
    return {"id": order_id}
