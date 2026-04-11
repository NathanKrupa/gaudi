"""
Immutable domain records.

Every class in this module is a frozen dataclass with **zero methods**
— pure values that describe facts, not objects with behavior. The
functional discipline is: if a piece of logic reads from a record,
it is a free function in ``pipeline.py``, not a method on the record.

This is deliberate and rubric-driven. ``docs/philosophy/functional.md``
catechism #1 treats frozen dataclasses as the primary building
block, and rubric check #8 says inheritance is used only for
``Protocol`` / ABC definitions — never to reuse behavior. A
``@property`` helper on a record is a mild form of that reuse; a
stricter Functional reading avoids it entirely. The Gaudí rule
``SMELL-014 LazyElement`` is correctly scoped to fire on exactly
this pattern under the Functional school, and removing the
helpers is the faithful response.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping


class CustomerStanding(Enum):
    GOOD = "good"
    HOLD = "hold"
    BANNED = "banned"


class OrderStatus(Enum):
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    email: str
    standing: CustomerStanding
    credit_limit: Decimal


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    unit_price: Decimal
    max_per_order: int
    category: str


@dataclass(frozen=True)
class InventoryLevel:
    sku: str
    on_hand: int
    reserved: int


@dataclass(frozen=True)
class PromoCode:
    code: str
    percent_off: int
    expires_at: datetime


@dataclass(frozen=True)
class LineItem:
    sku: str
    quantity: int


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_id: str
    line_items: tuple[LineItem, ...]
    promo_code: str | None
    shipping_address: str


@dataclass(frozen=True)
class Outcome:
    order_id: str
    status: OrderStatus
    final_price: Decimal | None
    reservation_id: str | None
    rejection_reason: str | None


@dataclass(frozen=True)
class World:
    """The entire input state of the order-processing system.

    A ``World`` is an immutable snapshot. ``process_order`` never
    mutates it; instead it returns ``(outcome, new_world)`` where
    the new world differs from the old only in the inventory column.
    """

    customers: Mapping[str, Customer]
    products: Mapping[str, Product]
    inventory: Mapping[str, InventoryLevel]
    promo_codes: Mapping[str, PromoCode]
    shipping_fee: Decimal
    now: datetime
