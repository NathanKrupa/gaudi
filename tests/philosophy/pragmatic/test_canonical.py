"""
End-to-end tests for the Pragmatic reference implementation of the
canonical order-processing task.

Uses the shared seed data at ``tests/philosophy/seed_data.py``
unchanged. Every acceptance criterion from
``docs/philosophy/canonical-task.md`` is exercised. The contrast with
the Classical tests is deliberately minimal — it is the *production*
code that looks different, not the tests — because both schools are
solving the same problem and must pass the same cases.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from tests.philosophy import seed_data
from tests.philosophy.pragmatic.canonical import pipeline

_NOW = datetime(2026, 4, 10, 12, 0, 0)


@pytest.fixture
def state() -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    list[dict[str, Any]],
]:
    """Fresh mutable state built from the shared seed data, per test."""
    customers = {c["customer_id"]: c for c in seed_data.CUSTOMERS}
    products = {p["sku"]: p for p in seed_data.PRODUCTS}
    # dict(i) is a shallow copy — the seed dicts contain only ints, so
    # shallow is enough to isolate per-test mutation.
    inventory = {i["sku"]: dict(i) for i in seed_data.INVENTORY}
    promo_codes = {p["code"]: p for p in seed_data.PROMO_CODES}
    notifications: list[dict[str, Any]] = []
    return customers, products, inventory, promo_codes, notifications


def _run(order_data: dict[str, Any], state_) -> dict[str, Any]:
    customers, products, inventory, promo_codes, notifications = state_
    return pipeline.process_order(
        order=order_data,
        customers=customers,
        products=products,
        inventory=inventory,
        promo_codes=promo_codes,
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
def test_pipeline_matches_expected_outcome(case: dict[str, Any], state) -> None:
    outcome = _run(case["order"], state)

    if case["expected_status"] == "confirmed":
        _assert_confirmed(case, outcome)
    elif case["expected_status"] == "rejected":
        _assert_rejected(case, outcome)
    else:
        pytest.fail(f"unknown expected_status in {case['name']}")

    _customers, _products, _inventory, _promo_codes, notifications = state
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


def test_confirmed_order_decrements_available_inventory(state) -> None:
    """Seed stock for WIDGET-01 is 100; after a 2-unit order confirms,
    a follow-up order for 99 must be rejected."""
    first = _run(seed_data.TEST_ORDERS[0]["order"], state)
    assert first["status"] == "confirmed"

    huge = _order("O-HUGE", (("WIDGET-01", 99),))
    second = _run(huge, state)
    assert second["status"] == "rejected", (
        "follow-up order should be rejected because the first order's "
        "reservation left only 98 available, not 99"
    )


def test_out_of_stock_order_does_not_partially_reserve(state) -> None:
    """Atomicity: a failed reservation must leave no line partially reserved."""
    mixed = _order("O-MIX", (("WIDGET-01", 5), ("EMPTY-01", 1)))
    assert _run(mixed, state)["status"] == "rejected"

    # If the mixed order had partially reserved WIDGET-01, this would fail.
    followup = _order("O-FOLLOW", (("WIDGET-01", 5),))
    assert _run(followup, state)["status"] == "confirmed"
