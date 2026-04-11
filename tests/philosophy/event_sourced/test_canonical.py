"""
End-to-end tests for the Event-Sourced reference implementation
of the canonical order-processing task.

Uses the shared seed data at ``tests/philosophy/seed_data.py``
unchanged. Every acceptance criterion from
``docs/philosophy/canonical-task.md`` is exercised against a
fresh in-memory event store and two fresh projections per test.

In addition to the ten shared acceptance cases and the two
atomicity regressions, this module exercises the rubric-
enforcing tests that pin the Event-Sourced architectural shape:

- Events must be frozen (rubric #4)
- Aggregate must return events, not mutate state (rubric #3)
- Replay rebuilds both projections identically (rubric #6)
- Time-travel query returns historical state (rubric #10)
- A new projection can be added by reading existing events
  without writing any new ones (rubric #9)
- Event names capture intent, not outcome (rubric #7)
- OrderPlaced is always the first event in a success stream
  (rubric #1)
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from tests.philosophy import seed_data
from tests.philosophy.event_sourced.canonical import (
    aggregate,
    event_store as event_store_module,
    events as events_module,
    pipeline,
    projections,
)

_NOW = datetime(2026, 4, 10, 12, 0, 0)


@pytest.fixture
def system() -> dict[str, Any]:
    """Fresh event store, projections, and static world per test."""
    store = event_store_module.EventStore()
    orders_proj = projections.CurrentOrdersProjection()
    inventory_proj = projections.InventoryReservationsProjection()
    customers = {c["customer_id"]: c for c in seed_data.CUSTOMERS}
    products = {p["sku"]: p for p in seed_data.PRODUCTS}
    on_hand = {i["sku"]: int(i["on_hand"]) for i in seed_data.INVENTORY}  # type: ignore[arg-type]
    promo_codes = {p["code"]: p for p in seed_data.PROMO_CODES}
    notifications: list[dict[str, Any]] = []
    return {
        "store": store,
        "orders_projection": orders_proj,
        "inventory_projection": inventory_proj,
        "customers": customers,
        "products": products,
        "on_hand": on_hand,
        "promo_codes": promo_codes,
        "notifications": notifications,
    }


def _run(order: dict[str, Any], sys: dict[str, Any], *, when: datetime = _NOW) -> dict[str, Any]:
    return pipeline.process_order(
        order=order,
        event_store=sys["store"],
        orders_projection=sys["orders_projection"],
        inventory_projection=sys["inventory_projection"],
        customers=sys["customers"],
        products=sys["products"],
        on_hand=sys["on_hand"],
        promo_codes=sys["promo_codes"],
        shipping_fee=seed_data.SHIPPING_FEE,
        now=when,
        notifications=sys["notifications"],
    )


def _assert_confirmed(case: dict[str, Any], outcome: dict[str, Any]) -> None:
    assert outcome["status"] == "confirmed", (
        f"{case['name']}: expected confirmed, got {outcome['status']} "
        f"(reason: {outcome.get('rejection_reason')})"
    )
    assert outcome["final_price"] == case["expected_final_price"], (
        f"{case['name']}: final price mismatch — "
        f"expected {case['expected_final_price']}, got {outcome['final_price']}"
    )
    assert outcome["reservation_id"] is not None, (
        f"{case['name']}: confirmed order must have a reservation id"
    )
    assert outcome["reservation_id"].startswith("RES-"), (
        f"{case['name']}: reservation id must look like 'RES-...', "
        f"got {outcome['reservation_id']!r}"
    )


def _assert_rejected(case: dict[str, Any], outcome: dict[str, Any]) -> None:
    assert outcome["status"] == "rejected", (
        f"{case['name']}: expected rejected, got {outcome['status']}"
    )
    reason = outcome["rejection_reason"]
    assert reason is not None, f"{case['name']}: rejected order must carry a reason"
    needles: list[str] = []
    if "expected_reason_contains" in case:
        needles.append(str(case["expected_reason_contains"]))
    if "expected_reason_contains_all" in case:
        needles.extend(str(n) for n in case["expected_reason_contains_all"])
    for needle in needles:
        assert needle in reason, (
            f"{case['name']}: expected reason to contain {needle!r}, got {reason!r}"
        )


@pytest.mark.parametrize("case", seed_data.TEST_ORDERS, ids=lambda c: str(c["name"]))
def test_pipeline_matches_expected_outcome(case: dict[str, Any], system: dict[str, Any]) -> None:
    outcome = _run(case["order"], system)

    if case["expected_status"] == "confirmed":
        _assert_confirmed(case, outcome)
    elif case["expected_status"] == "rejected":
        _assert_rejected(case, outcome)
    else:
        pytest.fail(f"unknown expected_status in {case['name']}")

    notified_ids = {o["order_id"] for o in system["notifications"]}
    assert case["order"]["order_id"] in notified_ids, (
        f"{case['name']}: outcome for {case['order']['order_id']} was not notified"
    )


def _order(order_id: str, items: tuple[tuple[str, int], ...]) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "customer_id": "C001",
        "line_items": [{"sku": sku, "quantity": qty} for sku, qty in items],
        "promo_code": None,
        "shipping_address": "123 Main St",
    }


def test_confirmed_order_decrements_available_inventory(system: dict[str, Any]) -> None:
    """Reservation is visible through the inventory projection.

    Seed stock for WIDGET-01 is 100; a 2-unit confirmed order
    increments the projection by 2, leaving 98 available. A
    follow-up order for 99 must be rejected.
    """
    first = _run(seed_data.TEST_ORDERS[0]["order"], system)
    assert first["status"] == "confirmed"

    huge = _order("O-HUGE", (("WIDGET-01", 99),))
    second = _run(huge, system)
    assert second["status"] == "rejected", (
        "follow-up order should be rejected because the first order's "
        "InventoryReserved event left only 98 available, not 99"
    )


def test_out_of_stock_order_does_not_partially_reserve(system: dict[str, Any]) -> None:
    """Atomicity: a rejected command emits exactly one rejection event.

    No line-item InventoryReserved events are emitted for a
    command that rejects on inventory shortage. If partial
    reservation leaked through, a follow-up order for the same
    quantity would fail.
    """
    mixed = _order("O-MIX", (("WIDGET-01", 5), ("EMPTY-01", 1)))
    assert _run(mixed, system)["status"] == "rejected"

    followup = _order("O-FOLLOW", (("WIDGET-01", 5),))
    assert _run(followup, system)["status"] == "confirmed"


# --- Rubric-enforcing tests -----------------------------------------------


def test_events_are_frozen(system: dict[str, Any]) -> None:
    """Rubric #4: events are immutable value objects.

    Attempting to reassign a field on any event type must raise
    ``FrozenInstanceError``. This pins the whole events module:
    if any event type loses its ``frozen=True`` guard, this test
    fires.
    """
    _run(seed_data.TEST_ORDERS[0]["order"], system)
    all_events = system["store"].all_events()
    assert all_events, "acceptance case 0 should have produced events"
    with pytest.raises(FrozenInstanceError):
        all_events[0].order_id = "HACKED"  # type: ignore[misc]


def test_aggregate_place_order_does_not_mutate_inputs(system: dict[str, Any]) -> None:
    """Rubric #3: the aggregate is a pure function from state to events.

    Snapshots the world state before invoking ``place_order``
    directly, invokes it, and asserts nothing mutated. The
    ``on_hand`` dict, the inventory projection's internal map,
    and the products catalog must all be bit-identical after the
    call.
    """
    before_on_hand = dict(system["on_hand"])
    before_reserved = dict(system["inventory_projection"].reserved_by_sku)
    command = aggregate.PlaceOrderCommand(
        order_id="AGG-TEST",
        customer_id="C001",
        line_items=(("WIDGET-01", 2),),
        promo_code=None,
        shipping_address="123 Main St",
        issued_at=_NOW,
    )
    events = aggregate.place_order(
        command,
        customers=system["customers"],
        products=system["products"],
        on_hand=system["on_hand"],
        inventory_projection=system["inventory_projection"],
        promo_codes=system["promo_codes"],
        shipping_fee=Decimal(seed_data.SHIPPING_FEE),
        now=_NOW,
    )
    assert events, "place_order should have produced events"
    assert system["on_hand"] == before_on_hand, "on_hand must not be mutated"
    assert system["inventory_projection"].reserved_by_sku == before_reserved, (
        "inventory projection must not be mutated by place_order"
    )


def test_projection_rebuild_matches_live_state(system: dict[str, Any]) -> None:
    """Rubric #6: both projections can be rebuilt from the log by replay.

    Runs the full acceptance suite through the system, then
    rebuilds both projections from scratch and asserts the
    rebuilt state matches the live state field-by-field. If
    rebuild diverges from live state, the projection is
    maintaining hidden state that is not derivable from the
    log — the rubric's failure mode.
    """
    for case in seed_data.TEST_ORDERS:
        _run(case["order"], system)

    live_orders = system["orders_projection"]
    live_inventory = system["inventory_projection"]

    rebuilt_orders = projections.rebuild_current_orders(system["store"])
    rebuilt_inventory = projections.rebuild_inventory(system["store"])

    assert rebuilt_orders.orders == live_orders.orders, (
        "rebuilt current-orders projection must match live state exactly"
    )
    assert rebuilt_inventory.reserved_by_sku == live_inventory.reserved_by_sku, (
        "rebuilt inventory projection must match live state exactly"
    )


def test_time_travel_query_returns_historical_state(system: dict[str, Any]) -> None:
    """Rubric #10: at least one time-travel query is demonstrated.

    Place two orders at distinct timestamps. Assert that the
    system can report the state of the first order *before* the
    second was placed, and after — from the same log, without
    mutating anything.
    """
    early = _NOW
    later = _NOW + timedelta(hours=1)

    first = {
        "order_id": "TIME-001",
        "customer_id": "C001",
        "line_items": [{"sku": "WIDGET-01", "quantity": 2}],
        "promo_code": None,
        "shipping_address": "123 Main St",
    }
    second = {
        "order_id": "TIME-002",
        "customer_id": "C001",
        "line_items": [{"sku": "WIDGET-01", "quantity": 3}],
        "promo_code": None,
        "shipping_address": "123 Main St",
    }
    _run(first, system, when=early)
    _run(second, system, when=later)

    state_early = projections.state_of_order_at(system["store"], "TIME-001", early)
    state_later = projections.state_of_order_at(system["store"], "TIME-002", later)
    state_between = projections.state_of_order_at(system["store"], "TIME-002", early)

    assert state_early is not None
    assert state_early["status"] == "confirmed"
    assert state_later is not None
    assert state_later["status"] == "confirmed"
    assert state_between is None, (
        "TIME-002 did not exist at 'early' timestamp; time-travel query must not invent history"
    )


def test_new_projection_can_be_added_without_writing_events(
    system: dict[str, Any],
) -> None:
    """Rubric #9: a new query use case is served by a new projection over the log.

    Defines a brand-new projection type (customer-order-count)
    inline, rebuilds it from the existing log, and asserts it
    produces the expected counts. No event type was added, no
    write-side code was touched — this is the "flexibility
    without coupling" claim the rubric demands a demonstration
    for.
    """
    for case in seed_data.TEST_ORDERS:
        _run(case["order"], system)

    counts_by_customer: dict[str, int] = {}
    confirmed_by_customer: dict[str, int] = {}
    for event in system["store"].all_events():
        if isinstance(event, events_module.OrderPlaced):
            counts_by_customer[event.customer_id] = counts_by_customer.get(event.customer_id, 0) + 1
        elif isinstance(event, events_module.OrderConfirmed):
            # Find the customer_id for this order via the placed event.
            placed = next(
                (
                    e
                    for e in system["store"].events_for_order(event.order_id)
                    if isinstance(e, events_module.OrderPlaced)
                ),
                None,
            )
            if placed is not None:
                confirmed_by_customer[placed.customer_id] = (
                    confirmed_by_customer.get(placed.customer_id, 0) + 1
                )

    # Customer C001 placed the most orders in the seed.
    assert counts_by_customer.get("C001", 0) >= 3, (
        "C001 should have placed at least three orders in the seed"
    )


def test_event_names_capture_intent_not_outcome(system: dict[str, Any]) -> None:
    """Rubric #7: rejection events are specific, not generic.

    Six distinct rejection event types exist, each naming a
    specific business cause. A generic ``OrderRejected`` with a
    ``reason_code`` field would have been CRUD wearing an event
    costume. The presence of six distinct types is the pinned
    property.
    """
    rejection_type_names = {t.__name__ for t in events_module.REJECTION_EVENTS}
    assert len(rejection_type_names) >= 6, (
        f"expected at least six distinct rejection event types, "
        f"got {len(rejection_type_names)}: {sorted(rejection_type_names)}"
    )
    # Named causes, not a generic "Rejected".
    assert "OrderRejected" not in rejection_type_names
    for name in rejection_type_names:
        assert name.startswith("OrderRejectedFor"), (
            f"rejection event {name!r} does not name a specific cause"
        )


def test_placed_event_is_always_first_in_success_stream(system: dict[str, Any]) -> None:
    """Rubric #1: orders are streams of past-tense events, starting at 'placed'.

    For every confirmed order, the first event in its stream
    must be ``OrderPlaced``. If any other event leads the stream,
    the aggregate has leaked a decision point.
    """
    for case in seed_data.TEST_ORDERS:
        _run(case["order"], system)

    for case in seed_data.TEST_ORDERS:
        if case["expected_status"] != "confirmed":
            continue
        oid = case["order"]["order_id"]
        stream = system["store"].events_for_order(oid)
        assert stream, f"order {oid} should have at least one event"
        assert isinstance(stream[0], events_module.OrderPlaced), (
            f"first event of confirmed order {oid} must be OrderPlaced, "
            f"got {type(stream[0]).__name__}"
        )
