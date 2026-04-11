"""
End-to-end tests for the Classical reference implementation of the
canonical order-processing task.

These tests exercise the pipeline against every seed-data test case in
``tests.philosophy.seed_data``. Each test case covers one or more
acceptance criteria from ``docs/philosophy/canonical-task.md``. The
shared seed data is used unchanged — the Classical implementation
owns no private test data, so the same fixture drives every school.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.philosophy import seed_data
from tests.philosophy.classical.canonical.domain.models import (
    LineItem,
    Order,
    OrderStatus,
)
from tests.philosophy.classical.canonical.pipeline import (
    InMemoryNotificationSender,
    OrderPipeline,
    build_pipeline,
)


@pytest.fixture
def pipeline_and_sender() -> tuple[OrderPipeline, InMemoryNotificationSender]:
    return build_pipeline(
        customer_seed=seed_data.CUSTOMERS,
        product_seed=seed_data.PRODUCTS,
        inventory_seed=seed_data.INVENTORY,
        promo_seed=seed_data.PROMO_CODES,
        shipping_fee=seed_data.SHIPPING_FEE,
    )


def _make_order(data: dict[str, object]) -> Order:
    line_items = tuple(
        LineItem(sku=str(item["sku"]), quantity=int(item["quantity"]))  # type: ignore[arg-type]
        for item in data["line_items"]  # type: ignore[union-attr]
    )
    return Order(
        order_id=str(data["order_id"]),
        customer_id=str(data["customer_id"]),
        line_items=line_items,
        promo_code=(str(data["promo_code"]) if data.get("promo_code") is not None else None),
        shipping_address=str(data["shipping_address"]),
    )


def _assert_confirmed(case: dict, outcome) -> None:
    assert outcome.status is OrderStatus.CONFIRMED, (
        f"{case['name']}: expected confirmed, got {outcome.status} "
        f"(reason: {outcome.rejection_reason})"
    )
    assert outcome.final_price == Decimal(str(case["expected_final_price"])), (
        f"{case['name']}: final price mismatch"
    )
    assert outcome.reservation_id is not None, (
        f"{case['name']}: confirmed order must have a reservation id"
    )


def _assert_rejected(case: dict, outcome) -> None:
    assert outcome.status is OrderStatus.REJECTED, (
        f"{case['name']}: expected rejected, got {outcome.status}"
    )
    assert outcome.rejection_reason is not None, (
        f"{case['name']}: rejected order must carry a reason"
    )
    needles: list[str] = []
    if "expected_reason_contains" in case:
        needles.append(str(case["expected_reason_contains"]))
    if "expected_reason_contains_all" in case:
        needles.extend(str(n) for n in case["expected_reason_contains_all"])
    for needle in needles:
        assert needle in outcome.rejection_reason, (
            f"{case['name']}: expected reason to contain {needle!r}, "
            f"got {outcome.rejection_reason!r}"
        )


@pytest.mark.parametrize("case", seed_data.TEST_ORDERS, ids=lambda c: str(c["name"]))
def test_pipeline_matches_expected_outcome(case, pipeline_and_sender):
    pipeline, sender = pipeline_and_sender
    order = _make_order(case["order"])  # type: ignore[arg-type]

    outcome = pipeline.process(order)

    if case["expected_status"] == "confirmed":
        _assert_confirmed(case, outcome)
    elif case["expected_status"] == "rejected":
        _assert_rejected(case, outcome)
    else:
        pytest.fail(f"unknown expected_status in {case['name']}")

    notified_ids = {o.order_id for o in sender.sent}
    assert order.order_id in notified_ids, (
        f"{case['name']}: outcome for {order.order_id} was not notified"
    )


def test_confirmed_order_decrements_available_inventory(pipeline_and_sender):
    """
    A confirmed order must actually consume inventory, not merely
    succeed. Seed stock for WIDGET-01 is 100; after a 2-unit order
    confirms, only 98 remain. A follow-up order for 99 must therefore
    be rejected, proving the reservation persisted.
    """
    pipeline, _sender = pipeline_and_sender
    first_case = _make_order(seed_data.TEST_ORDERS[0]["order"])  # type: ignore[arg-type]
    first = pipeline.process(first_case)
    assert first.status is OrderStatus.CONFIRMED

    huge_order = Order(
        order_id="O-HUGE",
        customer_id="C001",
        line_items=(LineItem(sku="WIDGET-01", quantity=99),),
        promo_code=None,
        shipping_address="123 Main St",
    )
    second = pipeline.process(huge_order)
    assert second.status is OrderStatus.REJECTED, (
        "follow-up order should be rejected because the first order's "
        "reservation left only 98 available, not 99"
    )


def _order(order_id: str, items: tuple[tuple[str, int], ...]) -> Order:
    return Order(
        order_id=order_id,
        customer_id="C001",
        line_items=tuple(LineItem(sku=sku, quantity=qty) for sku, qty in items),
        promo_code=None,
        shipping_address="123 Main St",
    )


def test_out_of_stock_order_does_not_partially_reserve(pipeline_and_sender):
    """Atomicity: a failed reservation must leave no line partially reserved."""
    pipeline, _sender = pipeline_and_sender
    mixed = _order("O-MIX", (("WIDGET-01", 5), ("EMPTY-01", 1)))
    assert pipeline.process(mixed).status is OrderStatus.REJECTED

    # If the mixed order had partially reserved WIDGET-01, this would fail.
    followup = _order("O-FOLLOW", (("WIDGET-01", 5),))
    assert pipeline.process(followup).status is OrderStatus.CONFIRMED
