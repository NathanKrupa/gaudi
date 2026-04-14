"""Fixture for PYD-ARCH-001: model_config is a Pydantic class variable, not a field."""

from pydantic import BaseModel


class User(BaseModel):
    model_config = {"strict": True, "frozen": True}
    name: str
    age: int
