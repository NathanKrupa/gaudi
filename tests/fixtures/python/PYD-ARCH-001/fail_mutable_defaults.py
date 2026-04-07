"""Fixture for PYD-ARCH-001: bare list/dict literals as Pydantic defaults."""

from pydantic import BaseModel


class Order(BaseModel):
    items: list = []
    metadata: dict = {}
