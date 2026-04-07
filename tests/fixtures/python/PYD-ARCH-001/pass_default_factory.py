"""Fixture for PYD-ARCH-001: Field(default_factory=...) is the safe form."""

from pydantic import BaseModel, Field


class Order(BaseModel):
    items: list = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
