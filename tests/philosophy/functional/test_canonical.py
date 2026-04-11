"""
End-to-end tests for the Functional reference implementation.

Uses the shared seed data at ``tests/philosophy/seed_data.py``
unchanged. Every acceptance criterion from
``docs/philosophy/canonical-task.md`` is exercised. The test shape
differs from the Classical and Pragmatic versions in one important
way: because ``process_order`` is pure and returns
``(outcome, new_world)``, the tests thread the world through
successive calls instead of mutating a shared dict.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

from tests.philosophy import seed_data
from tests.philosophy.functional.canonical.models import (
    Customer,
    CustomerStanding,
    InventoryLevel,
    LineItem,
    Order,
    OrderStatus,
    Product,
    PromoCode,
    World,
)
from tests.philosophy.functional.canonical.pipeline import process_order

_NOW = datetime(2026, 4, 10, 12, 0, 0)


def _build_customer(data: dict[str, Any]) -> Customer:
    return Customer(
        customer_id=str(data["customer_id"]),
        name=str(data["name"]),
        email=str(data["email"]),
        standing=CustomerStanding(str(data["standing"])),
        credit_limit=Decimal(str(data["credit_limit"])),
    )


def _build_product(data: dict[str, Any]) -> Product:
    return Product(
        sku=str(data["sku"]),
        name=str(data["name"]),
        unit_price=Decimal(str(data["unit_price"])),
        max_per_order=int(data["max_per_order"]),  # type: ignore[arg-type]
        category=str(data["category"]),
    )


def _build_level(data: dict[str, Any]) -> InventoryLevel:
    return InventoryLevel(
        sku=str(data["sku"]),
        on_hand=int(data["on_hand"]),  # type: ignore[arg-type]
        reserved=int(data["reserved"]),  # type: ignore[arg-type]
    )


def _build_promo(data: dict[str, Any]) -> PromoCode:
    return PromoCode(
        code=str(data["code"]),
        percent_off=int(data["percent_off"]),  # type: ignore[arg-type]
        expires_at=datetime.fromisoformat(str(data["expires_at"])),
    )


@pytest.fixture
def world() -> World:
    return World(
        customers={str(c["customer_id"]): _build_customer(c) for c in seed_data.CUSTOMERS},
        products={str(p["sku"]): _build_product(p) for p in seed_data.PRODUCTS},
        inventory={str(level["sku"]): _build_level(level) for level in seed_data.INVENTORY},
        promo_codes={str(p["code"]): _build_promo(p) for p in seed_data.PROMO_CODES},
        shipping_fee=Decimal(seed_data.SHIPPING_FEE),
        now=_NOW,
    )


def _make_order(data: dict[str, Any]) -> Order:
    return Order(
        order_id=str(data["order_id"]),
        customer_id=str(data["customer_id"]),
        line_items=tuple(
            LineItem(sku=str(item["sku"]), quantity=int(item["quantity"]))  # type: ignore[arg-type]
            for item in data["line_items"]  # type: ignore[union-attr]
        ),
        promo_code=(str(data["promo_code"]) if data.get("promo_code") is not None else None),
        shipping_address=str(data["shipping_address"]),
    )


def _assert_confirmed(case: dict[str, Any], outcome) -> None:
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


def _assert_rejected(case: dict[str, Any], outcome) -> None:
    assert outcome.status is OrderStatus.REJECTED, (
        f"{case['name']}: expected rejected, got {outcome.status}"
    )
    reason = outcome.rejection_reason
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
def test_pipeline_matches_expected_outcome(case: dict[str, Any], world: World) -> None:
    order = _make_order(case["order"])  # type: ignore[arg-type]
    outcome, new_world = process_order(order, world, reservation_id="RES-000001")

    if case["expected_status"] == "confirmed":
        _assert_confirmed(case, outcome)
        # A confirmed order must produce a new world whose inventory
        # differs from the original — the reservation was applied.
        assert new_world is not world or new_world.inventory is not world.inventory, (
            "confirmed order should produce a new world with updated inventory"
        )
    elif case["expected_status"] == "rejected":
        _assert_rejected(case, outcome)
        # A rejected order returns the world unchanged.
        assert new_world is world, "rejected order should return the world unchanged"
    else:
        pytest.fail(f"unknown expected_status in {case['name']}")


def _order(order_id: str, items: tuple[tuple[str, int], ...]) -> Order:
    return Order(
        order_id=order_id,
        customer_id="C001",
        line_items=tuple(LineItem(sku=sku, quantity=qty) for sku, qty in items),
        promo_code=None,
        shipping_address="123 Main St",
    )


def test_confirmed_order_decrements_available_inventory(world: World) -> None:
    """Threading state: the new world must reflect the first reservation."""
    first_order = _make_order(seed_data.TEST_ORDERS[0]["order"])  # type: ignore[arg-type]
    first_outcome, world1 = process_order(first_order, world, "RES-000001")
    assert first_outcome.status is OrderStatus.CONFIRMED

    # Stock was 100, first order reserved 2, so only 98 remain.
    huge = _order("O-HUGE", (("WIDGET-01", 99),))
    second_outcome, world2 = process_order(huge, world1, "RES-000002")
    assert second_outcome.status is OrderStatus.REJECTED, (
        "follow-up order should be rejected because world1's inventory "
        "left only 98 available, not 99"
    )
    # And the original world is unchanged — purity proven.
    assert world.inventory["WIDGET-01"].reserved == 0


def test_out_of_stock_order_does_not_partially_reserve(world: World) -> None:
    """Atomicity: a failed reservation returns the world unchanged."""
    mixed = _order("O-MIX", (("WIDGET-01", 5), ("EMPTY-01", 1)))
    first_outcome, world1 = process_order(mixed, world, "RES-000001")
    assert first_outcome.status is OrderStatus.REJECTED
    assert world1 is world, "rejection must leave the world untouched"

    # A pure WIDGET-01 order for the same quantity must still succeed,
    # because no partial reservation occurred above.
    followup = _order("O-FOLLOW", (("WIDGET-01", 5),))
    second_outcome, _world2 = process_order(followup, world1, "RES-000002")
    assert second_outcome.status is OrderStatus.CONFIRMED


def test_process_order_is_referentially_transparent(world: World) -> None:
    """The same call twice against the same world produces the same outcome.

    This is the Functional axiom's catechism #7 in test form.
    """
    order = _make_order(seed_data.TEST_ORDERS[0]["order"])  # type: ignore[arg-type]
    outcome1, world_a = process_order(order, world, "RES-000001")
    outcome2, world_b = process_order(order, world, "RES-000001")

    assert outcome1 == outcome2
    # The two new worlds are structurally identical — purity means
    # calling process_order twice on the same input produces two
    # equal results.
    assert world_a.inventory == world_b.inventory


def test_core_is_free_of_io_imports() -> None:
    """The functional core must not import logging, os, requests, or a clock.

    ``docs/philosophy/functional.md`` catechism #3: side effects
    are pushed to the edges. This test is the structural proof
    that the pipeline module does not reach for them.
    """
    import tests.philosophy.functional.canonical.pipeline as pipeline_module

    source = open(pipeline_module.__file__, encoding="utf-8").read()
    forbidden_imports = {
        "import logging",
        "import os",
        "import requests",
        "import sqlite3",
        "from time import",
    }
    found = {needle for needle in forbidden_imports if needle in source}
    assert not found, (
        f"pipeline.py imports forbidden I/O modules: {sorted(found)}. "
        "Side effects must be pushed to the edges."
    )
    # datetime is allowed only as a type for the ``now`` parameter —
    # the pipeline must not call ``datetime.now()``.
    assert "datetime.now(" not in source, (
        "pipeline.py must not call datetime.now() — time should be "
        "passed in as a value, not fetched from the clock."
    )


def _world_replace_inventory(world: World, inventory: dict) -> World:
    return replace(world, inventory=inventory)
