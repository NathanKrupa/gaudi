"""
End-to-end tests for the Data-Oriented reference implementation of
the canonical order-processing task.

Uses the shared seed data at ``tests/philosophy/seed_data.py``
unchanged. Every acceptance criterion from
``docs/philosophy/canonical-task.md`` is exercised against the
Struct-of-Arrays world built by ``state.build_world``. The batch
pipeline is also exercised directly at the end of the module so the
main API (``process_orders_batch``) is not only visible through its
single-order adapter.

Numpy is a test-only optional dependency (see pyproject.toml dev
extras). If numpy cannot be imported, the entire Data-Oriented test
module is skipped with a clear reason — CI on any Python version
that can install numpy runs these tests, and any environment that
cannot still stays green.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

pytest.importorskip(
    "numpy",
    reason="numpy is required for the Data-Oriented reference exemplar tests",
)

import numpy as np  # noqa: E402

from tests.philosophy import seed_data  # noqa: E402
from tests.philosophy.data_oriented.canonical import pipeline, state  # noqa: E402

_NOW = datetime(2026, 4, 10, 12, 0, 0)


@pytest.fixture
def world_and_notifications() -> tuple[state.World, list[dict[str, Any]]]:
    """Fresh world + empty notification log per test."""
    world = state.build_world(
        customers=seed_data.CUSTOMERS,
        products=seed_data.PRODUCTS,
        inventory=seed_data.INVENTORY,
        promo_codes=seed_data.PROMO_CODES,
    )
    notifications: list[dict[str, Any]] = []
    return world, notifications


def _run(
    order: dict[str, Any], world: state.World, notifications: list[dict[str, Any]]
) -> dict[str, Any]:
    return pipeline.process_order(
        order=order,
        world=world,
        shipping_fee=seed_data.SHIPPING_FEE,
        now=_NOW,
        notifications=notifications,
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
        f"{case['name']}: reservation id must look like 'RES-NNNNNN', "
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
def test_pipeline_matches_expected_outcome(
    case: dict[str, Any],
    world_and_notifications: tuple[state.World, list[dict[str, Any]]],
) -> None:
    world, notifications = world_and_notifications
    outcome = _run(case["order"], world, notifications)

    if case["expected_status"] == "confirmed":
        _assert_confirmed(case, outcome)
    elif case["expected_status"] == "rejected":
        _assert_rejected(case, outcome)
    else:
        pytest.fail(f"unknown expected_status in {case['name']}")

    notified_ids = {o["order_id"] for o in notifications}
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


def test_confirmed_order_decrements_available_inventory(
    world_and_notifications: tuple[state.World, list[dict[str, Any]]],
) -> None:
    """Reservation must update the inventory_reserved column in place."""
    world, notifications = world_and_notifications
    first = _run(seed_data.TEST_ORDERS[0]["order"], world, notifications)
    assert first["status"] == "confirmed"

    # Follow-up order for 99 of WIDGET-01: stock is 100, first order
    # reserved 2, so 98 are available. This must be rejected.
    huge = _order("O-HUGE", (("WIDGET-01", 99),))
    second = _run(huge, world, notifications)
    assert second["status"] == "rejected", (
        "follow-up order should be rejected because the first order's "
        "reservation left only 98 available, not 99"
    )


def test_out_of_stock_order_does_not_partially_reserve(
    world_and_notifications: tuple[state.World, list[dict[str, Any]]],
) -> None:
    """Atomicity: a failed reservation must leave no line partially reserved."""
    world, notifications = world_and_notifications
    mixed = _order("O-MIX", (("WIDGET-01", 5), ("EMPTY-01", 1)))
    assert _run(mixed, world, notifications)["status"] == "rejected"

    # If the mixed order had partially reserved WIDGET-01, a follow-
    # up for 5 more would hit the reservation wall and fail. It
    # must succeed.
    followup = _order("O-FOLLOW", (("WIDGET-01", 5),))
    assert _run(followup, world, notifications)["status"] == "confirmed"


# --- Rubric-enforcing tests -----------------------------------------------
# These pin the architectural shape the Data-Oriented axiom
# demands. If any of them fails, either the implementation drifted
# off the rubric or the rubric itself shifted — in which case
# docs/philosophy/data-oriented.md is the place to start the
# conversation, not the test.


def test_world_hot_columns_are_contiguous_numpy_arrays(
    world_and_notifications: tuple[state.World, list[dict[str, Any]]],
) -> None:
    """Rubric #3: at least one Struct-of-Arrays layout.

    Every hot column on the World must be a numpy ndarray with a
    concrete dtype. A list-of-dicts 'AoS' world would satisfy the
    test interface but violate the axiom.
    """
    world, _ = world_and_notifications
    hot_columns = (
        ("customer_credit_limit_cents", np.int64),
        ("customer_standing", np.uint8),
        ("product_unit_price_cents", np.int64),
        ("product_max_per_order", np.int32),
        ("inventory_on_hand", np.int32),
        ("inventory_reserved", np.int32),
    )
    for name, dtype in hot_columns:
        col = getattr(world, name)
        assert isinstance(col, np.ndarray), f"{name} must be an ndarray, got {type(col)}"
        assert col.dtype == np.dtype(dtype), (
            f"{name} must have dtype {np.dtype(dtype)}, got {col.dtype}"
        )


def test_world_is_frozen_against_column_rebinding() -> None:
    """Rubric #7: data structures described by access pattern.

    The World dataclass uses ``frozen=True, slots=True`` so a typo
    like ``world.credit_limit_cents = ...`` raises rather than
    silently introducing a new attribute that the hot loop will
    never see.
    """
    world = state.build_world(
        customers=seed_data.CUSTOMERS,
        products=seed_data.PRODUCTS,
        inventory=seed_data.INVENTORY,
        promo_codes=seed_data.PROMO_CODES,
    )
    with pytest.raises((AttributeError, TypeError)):
        world.customer_credit_limit_cents = np.zeros(1, dtype=np.int64)  # type: ignore[misc]


def test_batch_api_processes_multiple_orders_in_one_call(
    world_and_notifications: tuple[state.World, list[dict[str, Any]]],
) -> None:
    """Rubric #1: orders are processed in batches, not one-at-a-time.

    Exercises ``process_orders_batch`` directly with a small batch
    drawn from the seed (happy path + valid promo + on-hold
    rejection). All three outcomes must come back in one call in
    input order.
    """
    world, notifications = world_and_notifications
    orders = [
        seed_data.TEST_ORDERS[0]["order"],  # happy
        seed_data.TEST_ORDERS[1]["order"],  # valid promo
        seed_data.TEST_ORDERS[3]["order"],  # customer on hold -> rejected
    ]
    outcomes = pipeline.process_orders_batch(
        orders=orders,
        world=world,
        shipping_fee=seed_data.SHIPPING_FEE,
        now=_NOW,
        notifications=notifications,
    )

    assert len(outcomes) == 3
    assert outcomes[0]["status"] == "confirmed"
    assert outcomes[0]["final_price"] == "25.00"
    assert outcomes[1]["status"] == "confirmed"
    assert outcomes[1]["final_price"] == "50.00"
    assert outcomes[2]["status"] == "rejected"
    assert "standing" in (outcomes[2]["rejection_reason"] or "")
    # Outcomes are in input order.
    order_ids_out = [o["order_id"] for o in outcomes]
    assert order_ids_out == ["O001", "O002", "O004"]


def test_batch_with_multiple_confirmed_orders_accumulates_reservations(
    world_and_notifications: tuple[state.World, list[dict[str, Any]]],
) -> None:
    """Rubric #6: scatter-reduce via np.add.at on the reserved column.

    Two back-to-back single-line orders for the same sku in one
    batch must leave ``inventory_reserved[sku]`` incremented by
    the sum of both quantities. A raw indexed assignment would
    drop one of the two writes; np.add.at is the right primitive.
    """
    world, notifications = world_and_notifications
    orders = [
        _order("B001", (("WIDGET-01", 3),)),
        _order("B002", (("WIDGET-01", 4),)),
    ]
    outcomes = pipeline.process_orders_batch(
        orders=orders,
        world=world,
        shipping_fee=seed_data.SHIPPING_FEE,
        now=_NOW,
        notifications=notifications,
    )
    assert outcomes[0]["status"] == "confirmed"
    assert outcomes[1]["status"] == "confirmed"

    widget_idx = world.product_sku_to_idx["WIDGET-01"]
    assert int(world.inventory_reserved[widget_idx]) == 7, (
        "np.add.at must accumulate both reservations into the same "
        "inventory row; got "
        f"{int(world.inventory_reserved[widget_idx])}"
    )


def test_standing_code_is_packed_integer_not_string() -> None:
    """Rubric #8: Python-native performance tools used honestly.

    The customer-standing column is uint8 with three documented
    values (good/hold/banned), not a Python list of strings. A
    string-valued column would force a hash compare per row in
    the validate-customer stage.
    """
    world = state.build_world(
        customers=seed_data.CUSTOMERS,
        products=seed_data.PRODUCTS,
        inventory=seed_data.INVENTORY,
        promo_codes=seed_data.PROMO_CODES,
    )
    assert world.customer_standing.dtype == np.uint8
    # Exactly the three canonical values appear in the seed.
    observed = set(int(x) for x in world.customer_standing.tolist())
    assert observed == {state.STANDING_GOOD, state.STANDING_HOLD, state.STANDING_BANNED}


def test_prices_are_integer_cents_not_floats() -> None:
    """Rubric #6: no per-iteration Decimal allocation in the hot path.

    Money lives in int64 cents so the pricing stage can vectorize
    with SIMD-friendly integer math while keeping the acceptance
    tests' exact-string expectations. A float64 column would
    vectorize too but reintroduce the 0.1 + 0.2 = 0.30000… problem
    the other exemplars dodge with Decimal.
    """
    world = state.build_world(
        customers=seed_data.CUSTOMERS,
        products=seed_data.PRODUCTS,
        inventory=seed_data.INVENTORY,
        promo_codes=seed_data.PROMO_CODES,
    )
    assert world.product_unit_price_cents.dtype == np.int64
    assert world.customer_credit_limit_cents.dtype == np.int64
    # WIDGET-01 at 10.00 should be 1000 cents.
    w01 = world.product_sku_to_idx["WIDGET-01"]
    assert int(world.product_unit_price_cents[w01]) == 1000
