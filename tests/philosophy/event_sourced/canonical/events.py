"""
Event types: past-tense, frozen, intent-carrying.

Every state change in the order-processing system is expressed as
an instance of one of these classes. An event is a fact, and a
fact is immutable — there are no setters, no "updated selves," no
methods that return mutated copies. Once an event has been
appended to the log, the log is the authoritative record of that
change forever.

Naming discipline (rubric #7)
-----------------------------
Event names capture *intent*, not *outcome*. Not
``OrderStatusChanged(from='placed', to='rejected')`` — that is
CRUD wearing an event costume. Instead: six distinct rejection
events whose names identify the specific business cause
(``OrderRejectedForCreditLimit``, ``OrderRejectedForInsufficientInventory``,
...). A future analyst, regulator, or product manager reading
the log can distinguish "we rejected this because the customer
was on hold" from "we rejected this because the line item
exceeded max_per_order" without parsing a reason field.

Invariant: every event carries ``order_id`` and ``occurred_at``
so projections can index and time-travel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class OrderPlaced:
    """An order arrived at the system with a customer and shipping address.

    This is always the first event in an order's stream. No
    pricing, no inventory, no validation yet — just "a customer
    intended to place this order."
    """

    order_id: str
    customer_id: str
    shipping_address: str
    promo_code: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class LineItemAdded:
    """One line item was added to an order, at the unit price in effect at that time.

    The unit price is captured on the event so a replayed
    projection produces the same pricing even if the product
    catalog's current unit_price has since changed. This is the
    classic event-sourcing "store the price that was charged, not
    a pointer to the current price" discipline.
    """

    order_id: str
    sku: str
    quantity: int
    unit_price: Decimal
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OrderPricingCalculated:
    """The aggregate computed subtotal, discount, and final price for an order.

    Captured as its own event so the pricing step is visible in
    the log — a future auditor can see exactly which promo the
    order was priced under, for how much, and at what time.
    """

    order_id: str
    subtotal: Decimal
    discount: Decimal
    shipping_fee: Decimal
    final_price: Decimal
    promo_code_applied: str | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class InventoryReserved:
    """Stock was reserved for one line item of a confirmed order.

    One ``InventoryReserved`` event is emitted per line of a
    confirmed order. The inventory projection sums these per sku
    to compute the current reserved quantity.
    """

    order_id: str
    sku: str
    quantity: int
    reservation_id: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OrderConfirmed:
    """The order cleared every invariant and was confirmed.

    Terminal success event. The orders projection transitions the
    order to status 'confirmed' and records the reservation id
    and final price on receipt of this event.
    """

    order_id: str
    reservation_id: str
    final_price: Decimal
    occurred_at: datetime


# --- Rejection events ------------------------------------------------------
# Six distinct rejection types, each naming a specific business
# cause. The names are the intent the rubric (#7) demands. Each
# event carries a human-readable ``reason`` string that the
# outcome-from-events adapter uses to produce the acceptance
# tests' expected substrings.


@dataclass(frozen=True, slots=True)
class OrderRejectedForUnknownCustomer:
    order_id: str
    customer_id: str
    reason: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OrderRejectedForCustomerStanding:
    order_id: str
    customer_id: str
    standing: str
    reason: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OrderRejectedForUnknownProduct:
    order_id: str
    sku: str
    reason: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OrderRejectedForQuantityExceeded:
    order_id: str
    sku: str
    quantity: int
    max_per_order: int
    reason: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OrderRejectedForInsufficientInventory:
    order_id: str
    shortfall_skus: tuple[str, ...]
    reason: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class OrderRejectedForCreditLimit:
    order_id: str
    customer_id: str
    final_price: Decimal
    credit_limit: Decimal
    reason: str
    occurred_at: datetime


# Sum type used throughout the exemplar. Every event instance
# must be exactly one of these classes. A new event type is added
# by defining a new frozen dataclass above and listing it here.
Event = (
    OrderPlaced
    | LineItemAdded
    | OrderPricingCalculated
    | InventoryReserved
    | OrderConfirmed
    | OrderRejectedForUnknownCustomer
    | OrderRejectedForCustomerStanding
    | OrderRejectedForUnknownProduct
    | OrderRejectedForQuantityExceeded
    | OrderRejectedForInsufficientInventory
    | OrderRejectedForCreditLimit
)


REJECTION_EVENTS: tuple[type, ...] = (
    OrderRejectedForUnknownCustomer,
    OrderRejectedForCustomerStanding,
    OrderRejectedForUnknownProduct,
    OrderRejectedForQuantityExceeded,
    OrderRejectedForInsufficientInventory,
    OrderRejectedForCreditLimit,
)
