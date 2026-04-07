"""Fixture for FAPI-ARCH-001: FastAPI endpoint without response_model."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    return {"id": order_id}
