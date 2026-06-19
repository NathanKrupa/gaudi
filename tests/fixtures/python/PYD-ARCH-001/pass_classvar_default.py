"""Fixture for PYD-ARCH-001: a ClassVar mutable value is not an instance field.

A ClassVar is a class attribute shared by design, not a per-instance default,
so a mutable value there is not the hidden-state trap the rule targets.
"""

from typing import ClassVar

from pydantic import BaseModel


class Order(BaseModel):
    DEFAULTS: ClassVar[dict] = {"currency": "USD"}
    ALLOWED: ClassVar[list] = ["a", "b"]
    qty: int = 1
