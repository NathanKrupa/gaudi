"""
Domain value objects for the order-processing pipeline.

Every class here is a frozen dataclass whose invariants are enforced
at construction time via ``__post_init__``. The domain has no
infrastructure dependencies: nothing in this module imports from
``services``, ``infrastructure``, or any external system. A Customer
is a value; it has no behavior that reaches outside its own fields.

The exemplar deliberately refuses a Money value object. Classical
faithfulness includes refusing patterns that are not earning their
weight (see the rubric in ``docs/philosophy/classical.md`` #9): this
pipeline has no multi-currency requirement, so wrapping ``Decimal``
in a Money class would be pattern-worship, not discipline. Should a
second currency ever be introduced, Money becomes justified — and
that is when it would be extracted, under the Rule-of-Three
discipline that Pragmatic and Classical happen to share.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class CustomerStanding(Enum):
    """The permitted states of a customer's account standing."""

    GOOD = "good"
    HOLD = "hold"
    BANNED = "banned"


class OrderStatus(Enum):
    """The terminal states of an order after processing."""

    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Customer:
    """A customer identified by an opaque id, with a standing and credit limit."""

    customer_id: str
    name: str
    email: str
    standing: CustomerStanding
    credit_limit: Decimal

    def __post_init__(self) -> None:
        if self.credit_limit < Decimal(0):
            raise ValueError(
                f"Customer {self.customer_id} credit_limit must be non-negative, "
                f"got {self.credit_limit}"
            )

    @property
    def may_place_orders(self) -> bool:
        return self.standing is CustomerStanding.GOOD


@dataclass(frozen=True)
class Product:
    """A product available for order, identified by SKU."""

    sku: str
    name: str
    unit_price: Decimal
    max_per_order: int
    category: str

    def __post_init__(self) -> None:
        if self.unit_price < Decimal(0):
            raise ValueError(
                f"Product {self.sku} unit_price must be non-negative, got {self.unit_price}"
            )
        if self.max_per_order < 1:
            raise ValueError(
                f"Product {self.sku} max_per_order must be >= 1, got {self.max_per_order}"
            )


@dataclass(frozen=True)
class InventoryLevel:
    """The current stock level for a single SKU."""

    sku: str
    on_hand: int
    reserved: int

    def __post_init__(self) -> None:
        prefix = f"Inventory {self.sku}"
        if self.on_hand < 0:
            raise ValueError(f"{prefix} on_hand must be >= 0, got {self.on_hand}")
        if self.reserved < 0:
            raise ValueError(f"{prefix} reserved must be >= 0, got {self.reserved}")
        if self.reserved > self.on_hand:
            raise ValueError(
                f"{prefix} reserved ({self.reserved}) cannot exceed on_hand ({self.on_hand})"
            )

    @property
    def available(self) -> int:
        return self.on_hand - self.reserved


@dataclass(frozen=True)
class PromoCode:
    """A promotional discount code with an expiry timestamp."""

    code: str
    percent_off: int
    expires_at: datetime

    def __post_init__(self) -> None:
        if not 0 <= self.percent_off <= 100:
            raise ValueError(
                f"PromoCode {self.code} percent_off must be 0..100, got {self.percent_off}"
            )

    def is_active(self, as_of: datetime) -> bool:
        return as_of < self.expires_at


@dataclass(frozen=True)
class LineItem:
    """A single line on an order: a SKU and a positive quantity."""

    sku: str
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError(f"LineItem {self.sku} quantity must be > 0, got {self.quantity}")


@dataclass(frozen=True)
class Order:
    """An unprocessed customer order — a request awaiting the pipeline's decision."""

    order_id: str
    customer_id: str
    line_items: tuple[LineItem, ...]
    promo_code: str | None
    shipping_address: str

    def __post_init__(self) -> None:
        if not self.line_items:
            raise ValueError(f"Order {self.order_id} must contain at least one line item")
        if not self.shipping_address.strip():
            raise ValueError(f"Order {self.order_id} shipping_address must not be empty")


@dataclass(frozen=True)
class OrderOutcome:
    """The terminal result of running an order through the processing pipeline."""

    order_id: str
    status: OrderStatus
    final_price: Decimal | None
    reservation_id: str | None
    rejection_reason: str | None

    def __post_init__(self) -> None:
        if self.status is OrderStatus.CONFIRMED:
            confirmed = f"Confirmed order {self.order_id}"
            if self.final_price is None:
                raise ValueError(f"{confirmed} must have a final_price")
            if self.reservation_id is None:
                raise ValueError(f"{confirmed} must have a reservation_id")
            if self.rejection_reason is not None:
                raise ValueError(f"{confirmed} must not carry a rejection_reason")
        elif self.rejection_reason is None:
            raise ValueError(f"Rejected order {self.order_id} must have a rejection_reason")
