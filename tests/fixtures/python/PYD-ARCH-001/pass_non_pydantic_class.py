"""Fixture for PYD-ARCH-001: a plain class (not a Pydantic model) is out of scope."""

from pydantic import BaseModel  # imported but unused on this class


class Bag:
    items: list = []
    metadata: dict = {}


_ = BaseModel  # silence unused import
