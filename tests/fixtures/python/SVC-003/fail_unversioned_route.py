"""Fixture for SVC-003: a fastapi route with no version prefix."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    return {"id": order_id}
