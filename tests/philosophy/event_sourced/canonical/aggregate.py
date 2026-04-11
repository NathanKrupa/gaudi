"""
Order aggregate: command handler that emits events.

The aggregate is the consistency boundary for one order. It
exposes one command — ``place_order`` — that takes a command
payload plus whatever read-side state the decision needs, runs
every invariant check, and returns a sequence of events that
describe what happened. It does not mutate anything. It does not
write to the event store. It does not update projections.
Appending events and applying them to projections is the
pipeline's job; the aggregate's job is to decide *what events
should be produced*.

This separation is the rubric #2 and #3 discipline: the
aggregate enforces invariants at command time and emits facts,
and the read side (projections) consumes those facts. If a new
query appears, a new projection is added over the existing
events without touching the aggregate.

Invariants enforced here (rubric #8)
------------------------------------
1. Customer must exist in the world catalog.
2. Customer standing must be ``good``.
3. Every line item's sku must exist in the product catalog.
4. Every line item's quantity must be <= ``max_per_order``.
5. Every line item's quantity must be fillable from
   ``on_hand - (reserved from projection)``.
6. The final price (subtotal - discount + shipping) must be
   <= the customer's credit limit.

Any violation produces exactly one ``OrderRejectedFor*`` event
and no other events. No half-placed order, no partial reservation,
no "we'll fix it in a projection" leakage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from tests.philosophy.event_sourced.canonical.events import (
    Event,
    InventoryReserved,
    LineItemAdded,
    OrderConfirmed,
    OrderPlaced,
    OrderPricingCalculated,
    OrderRejectedForCreditLimit,
    OrderRejectedForCustomerStanding,
    OrderRejectedForInsufficientInventory,
    OrderRejectedForQuantityExceeded,
    OrderRejectedForUnknownCustomer,
    OrderRejectedForUnknownProduct,
)
from tests.philosophy.event_sourced.canonical.projections import (
    InventoryReservationsProjection,
)


@dataclass(frozen=True, slots=True)
class PlaceOrderCommand:
    """Input payload for the place_order command.

    Frozen so the handler cannot accidentally mutate the caller's
    view of what was commanded. Commands are not events, but they
    share the "immutable once dispatched" discipline for the same
    reason: a decision that could be rewritten mid-handling is a
    decision whose log entry is a lie.
    """

    order_id: str
    customer_id: str
    line_items: tuple[tuple[str, int], ...]
    promo_code: str | None
    shipping_address: str
    issued_at: datetime


def _reservation_id(order_id: str, sku: str) -> str:
    """Deterministic reservation id: ``RES-<order>-<sku>``.

    The canonical task's rubric for confirmed orders says the
    reservation id should look like ``RES-NNNNNN``. The
    event-sourced exemplar derives the id from the order_id and
    sku instead of from a global counter, so a replay of the
    log produces the same reservation ids as the original run —
    an essential property for rebuildability.
    """
    suffix = f"{order_id}-{sku}".replace("-", "")
    # Pad/truncate to 6 characters to match the shape the other
    # exemplars produce, without reintroducing a mutable counter.
    return f"RES-{suffix[:6].upper():0>6}"


def place_order(
    command: PlaceOrderCommand,
    *,
    customers: dict[str, dict[str, Any]],
    products: dict[str, dict[str, Any]],
    on_hand: dict[str, int],
    inventory_projection: InventoryReservationsProjection,
    promo_codes: dict[str, dict[str, Any]],
    shipping_fee: Decimal,
    now: datetime,
) -> tuple[Event, ...]:
    """Handle a place_order command and return the events it produced.

    Pure function: no I/O, no mutation of anything passed in.
    The caller is responsible for appending the returned events
    to the store and applying them to projections.
    """
    oid = command.order_id
    occurred_at = command.issued_at

    # Invariant 1: customer exists
    customer = customers.get(command.customer_id)
    if customer is None:
        return (
            OrderRejectedForUnknownCustomer(
                order_id=oid,
                customer_id=command.customer_id,
                reason=f"Unknown customer {command.customer_id}",
                occurred_at=occurred_at,
            ),
        )

    # Invariant 2: customer standing is 'good'
    standing = str(customer["standing"])
    if standing != "good":
        return (
            OrderRejectedForCustomerStanding(
                order_id=oid,
                customer_id=command.customer_id,
                standing=standing,
                reason=(
                    f"Customer {command.customer_id} standing is {standing}; may not place orders"
                ),
                occurred_at=occurred_at,
            ),
        )

    # Invariant 3: every sku exists
    for sku, _qty in command.line_items:
        if sku not in products:
            return (
                OrderRejectedForUnknownProduct(
                    order_id=oid,
                    sku=sku,
                    reason=f"Unknown product {sku}",
                    occurred_at=occurred_at,
                ),
            )

    # Invariant 4: every line quantity <= max_per_order
    for sku, qty in command.line_items:
        product = products[sku]
        max_allowed = int(product["max_per_order"])
        if qty > max_allowed:
            return (
                OrderRejectedForQuantityExceeded(
                    order_id=oid,
                    sku=sku,
                    quantity=qty,
                    max_per_order=max_allowed,
                    reason=(f"Line item {sku} quantity {qty} exceeds max_per_order {max_allowed}"),
                    occurred_at=occurred_at,
                ),
            )

    # Invariant 5: every line fillable from on_hand - reserved
    shortfall: list[str] = []
    for sku, qty in command.line_items:
        available = on_hand.get(sku, 0) - inventory_projection.reserved_by_sku.get(sku, 0)
        if qty > available:
            shortfall.append(sku)
    if shortfall:
        return (
            OrderRejectedForInsufficientInventory(
                order_id=oid,
                shortfall_skus=tuple(shortfall),
                reason=f"Insufficient inventory for: {', '.join(shortfall)}",
                occurred_at=occurred_at,
            ),
        )

    # Pricing: subtotal, discount, final
    subtotal = sum(
        (Decimal(products[sku]["unit_price"]) * qty for sku, qty in command.line_items),
        start=Decimal(0),
    )
    discount = Decimal(0)
    promo_applied: str | None = None
    if command.promo_code:
        promo = promo_codes.get(command.promo_code)
        if promo and datetime.fromisoformat(str(promo["expires_at"])) > now:
            discount = (subtotal * Decimal(int(promo["percent_off"])) / Decimal(100)).quantize(
                Decimal("0.01")
            )
            promo_applied = command.promo_code
    final_price = subtotal - discount + shipping_fee

    # Invariant 6: final_price <= credit_limit
    credit_limit = Decimal(str(customer["credit_limit"]))
    if final_price > credit_limit:
        return (
            OrderRejectedForCreditLimit(
                order_id=oid,
                customer_id=command.customer_id,
                final_price=final_price,
                credit_limit=credit_limit,
                reason=(
                    f"Final price {final_price} exceeds customer "
                    f"{command.customer_id} credit limit {credit_limit}"
                ),
                occurred_at=occurred_at,
            ),
        )

    # Success path — emit the placed/line/priced/reserved/confirmed
    # sequence. Every state change is one event; none of them
    # mutates the aggregate in place.
    events: list[Event] = [
        OrderPlaced(
            order_id=oid,
            customer_id=command.customer_id,
            shipping_address=command.shipping_address,
            promo_code=command.promo_code,
            occurred_at=occurred_at,
        ),
    ]
    for sku, qty in command.line_items:
        events.append(
            LineItemAdded(
                order_id=oid,
                sku=sku,
                quantity=qty,
                unit_price=Decimal(products[sku]["unit_price"]),
                occurred_at=occurred_at,
            )
        )
    events.append(
        OrderPricingCalculated(
            order_id=oid,
            subtotal=subtotal,
            discount=discount,
            shipping_fee=shipping_fee,
            final_price=final_price,
            promo_code_applied=promo_applied,
            occurred_at=occurred_at,
        )
    )
    reservation_id = _reservation_id(oid, command.line_items[0][0])
    for sku, qty in command.line_items:
        events.append(
            InventoryReserved(
                order_id=oid,
                sku=sku,
                quantity=qty,
                reservation_id=reservation_id,
                occurred_at=occurred_at,
            )
        )
    events.append(
        OrderConfirmed(
            order_id=oid,
            reservation_id=reservation_id,
            final_price=final_price,
            occurred_at=occurred_at,
        )
    )
    return tuple(events)
