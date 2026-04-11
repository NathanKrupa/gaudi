"""
Pragmatic / Evolutionary reference implementation of the canonical
order-processing task.

One function, one file. No Repository Protocol, no service layer, no
Clock abstraction, no ``OrderOutcome`` dataclass. The in-memory state
is plain dicts built by the caller from the shared seed data. If and
when a second storage backend or a second pricing policy appears, the
Rule of Three fires and we extract — not a line sooner.

Deliberate refusals (each is the *absence* of a thing the Classical
exemplar has at the same spot):

- **No Repository classes.** The ``customers`` / ``products`` /
  ``inventory`` / ``promo_codes`` parameters are plain dicts, read and
  mutated in place. There is no Protocol to speak of, because there is
  no second backend to abstract over yet.
- **No ``OrderOutcome`` dataclass or ``OrderStatus`` enum.** The
  outcome is a plain dict with well-named keys. A new team member can
  read ``outcome["status"] == "confirmed"`` without learning a type
  system.
- **No ``Clock`` Protocol.** ``process_order`` accepts ``now: datetime``
  directly from its caller, which is also where the test gets to pin
  time deterministically.
- **No separate ``ValidationService`` / ``PricingService`` /
  ``ReservationService`` / ``NotificationService``.** The four stages
  are sequential blocks in one function. Each block's purpose is
  obvious from its first line, and the whole flow reads top-to-bottom.

Honest duplication (rubric #1): two per-line loops iterate
``order["line_items"]`` — one validates ``max_per_order``, one checks
stock. They look similar but ask different questions and produce
different rejection shapes (fail on first vs. accumulate all
shortfalls). Fusing them would save a handful of lines and cost the
reader the cleanest possible reading of "first validate, then check
stock." Two similar loops is a coincidence; three would be a pattern.
"""

from __future__ import annotations

import itertools
from datetime import datetime
from decimal import Decimal
from typing import Any

Outcome = dict[str, Any]

# Module-level monotonic counter for reservation IDs. Plain Python
# idiom; no need for a factory class until a second generator appears.
_reservation_counter = itertools.count(1)


def _next_reservation_id() -> str:
    return f"RES-{next(_reservation_counter):06d}"


def process_order(
    order: dict[str, Any],
    customers: dict[str, dict[str, Any]],
    products: dict[str, dict[str, Any]],
    inventory: dict[str, dict[str, int]],
    promo_codes: dict[str, dict[str, Any]],
    shipping_fee: str,
    now: datetime,
    notifications: list[Outcome],
) -> Outcome:
    """Process one order end-to-end and return its terminal outcome.

    Mutates ``inventory`` to record the reservation and appends the
    outcome to ``notifications``. Every confirmed or rejected order is
    notified.
    """
    # Validate customer -----------------------------------------------------
    customer = customers.get(order["customer_id"])
    if customer is None:
        return _reject(order, f"Unknown customer {order['customer_id']}", notifications)
    if customer["standing"] != "good":
        return _reject(
            order,
            (
                f"Customer {customer['customer_id']} standing is "
                f"{customer['standing']}; may not place orders"
            ),
            notifications,
        )

    # Resolve + validate each line item ------------------------------------
    resolved: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for line in order["line_items"]:
        product = products.get(line["sku"])
        if product is None:
            return _reject(order, f"Unknown product {line['sku']}", notifications)
        if line["quantity"] > product["max_per_order"]:
            return _reject(
                order,
                (
                    f"Line item {line['sku']} quantity {line['quantity']} "
                    f"exceeds max_per_order {product['max_per_order']}"
                ),
                notifications,
            )
        resolved.append((product, line))

    # Check inventory for every resolved line ------------------------------
    # Honest duplication: this loop iterates resolved items just like
    # the previous one, but asks a different question (stock vs.
    # max_per_order) and accumulates every shortfall instead of
    # failing on the first. Don't fuse.
    insufficient: list[str] = []
    for product, line in resolved:
        level = inventory.get(product["sku"])
        available = (level["on_hand"] - level["reserved"]) if level else 0
        if available < line["quantity"]:
            insufficient.append(product["sku"])
    if insufficient:
        return _reject(
            order,
            f"Insufficient inventory for: {', '.join(insufficient)}",
            notifications,
        )

    # Pricing --------------------------------------------------------------
    subtotal = sum(
        (Decimal(p["unit_price"]) * line["quantity"] for p, line in resolved),
        start=Decimal(0),
    )
    discount = Decimal(0)
    code = order.get("promo_code")
    if code:
        promo = promo_codes.get(code)
        if promo and datetime.fromisoformat(promo["expires_at"]) > now:
            discount = (subtotal * Decimal(promo["percent_off"]) / Decimal(100)).quantize(
                Decimal("0.01")
            )
    final_price = subtotal - discount + Decimal(shipping_fee)

    # Credit-limit check ---------------------------------------------------
    if final_price > Decimal(customer["credit_limit"]):
        return _reject(
            order,
            (
                f"Final price {final_price} exceeds customer "
                f"{customer['customer_id']} credit limit {customer['credit_limit']}"
            ),
            notifications,
        )

    # Atomic reservation ---------------------------------------------------
    # We already checked availability above, so this loop cannot fail
    # halfway through under single-threaded execution. TODO: when a
    # second, concurrent order-processing caller is introduced, this
    # unchecked reserve loop becomes a race and needs synchronisation
    # or a compare-and-swap primitive. Revisit when the second caller
    # materialises.
    for product, line in resolved:
        inventory[product["sku"]]["reserved"] += line["quantity"]

    outcome: Outcome = {
        "order_id": order["order_id"],
        "status": "confirmed",
        "final_price": str(final_price),
        "reservation_id": _next_reservation_id(),
        "rejection_reason": None,
    }
    notifications.append(outcome)
    return outcome


def _reject(order: dict[str, Any], reason: str, notifications: list[Outcome]) -> Outcome:
    outcome: Outcome = {
        "order_id": order["order_id"],
        "status": "rejected",
        "final_price": None,
        "reservation_id": None,
        "rejection_reason": reason,
    }
    notifications.append(outcome)
    return outcome
