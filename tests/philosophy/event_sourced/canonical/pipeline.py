"""
Event-Sourced pipeline: the glue that wires commands to the log and projections.

``process_order`` is the entry point the test harness uses. It
takes the same external shape every other exemplar exposes —
plain dict input, plain dict output — and wraps the event-sourced
machinery behind it:

    command -> aggregate.place_order -> events -> store.append_many -> projections.apply

The pipeline is the only place where events become state-visible.
The aggregate is pure (it takes state and returns events without
mutation); the projections are pure (they apply events without
reading anywhere else); the pipeline composes them and handles
the one impure thing in the system — writing to the log.

Deliberate refusals (each is the absence of a thing the other
exemplars have at the same spot):

- **No in-place order mutation.** There is no ``order.status =
  "confirmed"`` statement anywhere in the exemplar. The only way
  state changes is by appending an event.
- **No CRUD on the event store.** The store exposes ``append``
  and read methods. There is no ``update``, ``delete``, or
  ``replace``. Corrections (not needed for the canonical task)
  would be appended as compensating events.
- **No projection as source of truth.** Projections are rebuilt
  from the log on demand. If they disagree with the log, the
  log wins, and the test suite exercises that rebuild.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from tests.philosophy.event_sourced.canonical.aggregate import (
    PlaceOrderCommand,
    place_order,
)
from tests.philosophy.event_sourced.canonical.event_store import EventStore
from tests.philosophy.event_sourced.canonical.events import (
    Event,
    OrderConfirmed,
    OrderPricingCalculated,
)
from tests.philosophy.event_sourced.canonical.projections import (
    CurrentOrdersProjection,
    InventoryReservationsProjection,
)

Outcome = dict[str, Any]


def process_order(
    order: dict[str, Any],
    *,
    event_store: EventStore,
    orders_projection: CurrentOrdersProjection,
    inventory_projection: InventoryReservationsProjection,
    customers: dict[str, dict[str, Any]],
    products: dict[str, dict[str, Any]],
    on_hand: dict[str, int],
    promo_codes: dict[str, dict[str, Any]],
    shipping_fee: str,
    now: datetime,
    notifications: list[Outcome],
) -> Outcome:
    """Process one order command and return its outcome dict.

    The outcome shape is the same as every other exemplar so the
    acceptance tests can compare apples to apples. Internally,
    this function translates the dict into a command, invokes the
    aggregate, appends the resulting events, updates both
    projections, and then derives the outcome dict from the
    events themselves — never from mutable state.
    """
    command = PlaceOrderCommand(
        order_id=str(order["order_id"]),
        customer_id=str(order["customer_id"]),
        line_items=tuple((str(item["sku"]), int(item["quantity"])) for item in order["line_items"]),
        promo_code=(str(order["promo_code"]) if order.get("promo_code") else None),
        shipping_address=str(order.get("shipping_address", "")),
        issued_at=now,
    )

    events = place_order(
        command,
        customers=customers,
        products=products,
        on_hand=on_hand,
        inventory_projection=inventory_projection,
        promo_codes=promo_codes,
        shipping_fee=Decimal(shipping_fee),
        now=now,
    )

    event_store.append_many(events)
    for event in events:
        orders_projection.apply(event)
        inventory_projection.apply(event)

    outcome = _outcome_from_events(command.order_id, events)
    notifications.append(outcome)
    return outcome


def _outcome_from_events(order_id: str, events: tuple[Event, ...]) -> Outcome:
    """Build the acceptance-test outcome dict from the event sequence.

    This function is the adapter between the event-sourced world
    and the shared outcome shape the other exemplars use. It
    reads from the events — never from a projection — because the
    events are the authoritative record of what happened.
    """
    confirmed: OrderConfirmed | None = None
    pricing: OrderPricingCalculated | None = None
    rejection_reason: str | None = None

    for event in events:
        if isinstance(event, OrderConfirmed):
            confirmed = event
        elif isinstance(event, OrderPricingCalculated):
            pricing = event
        elif hasattr(event, "reason"):
            rejection_reason = str(event.reason)  # type: ignore[attr-defined]

    if confirmed is not None:
        final_price = confirmed.final_price
        if pricing is not None:
            final_price = pricing.final_price
        return {
            "order_id": order_id,
            "status": "confirmed",
            "final_price": str(final_price.quantize(Decimal("0.01"))),
            "reservation_id": confirmed.reservation_id,
            "rejection_reason": None,
        }

    return {
        "order_id": order_id,
        "status": "rejected",
        "final_price": None,
        "reservation_id": None,
        "rejection_reason": rejection_reason,
    }
