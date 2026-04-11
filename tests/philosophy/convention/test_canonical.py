"""
End-to-end tests for the Convention reference implementation.

These tests run against a real Django in-memory SQLite database.
The module bootstraps Django via ``django.setup()`` and uses
``call_command("migrate")`` to create the schema before any test
runs. Each test lives inside a transaction that is rolled back at
the end, so tests are isolated without needing fixtures to rebuild
state manually.

Uses the shared seed data at ``tests/philosophy/seed_data.py``
unchanged. Every acceptance criterion from
``docs/philosophy/canonical-task.md`` is exercised.
"""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import Any

import pytest

# Django is a test-only optional dependency (see pyproject.toml dev
# extras). It is pinned to 5.x LTS for Python < 3.14 and unpinned
# for 3.14 where support is uncertain. If Django is not installed,
# skip the entire Convention test module with a clear reason —
# this lets CI on Python 3.14 stay green when Django 5.x cannot be
# installed there.
django = pytest.importorskip(
    "django",
    reason="Django is required for the Convention reference exemplar tests",
)

# Django must be configured before any model import. The settings
# module is a normal Python import path; the pytest rootconftest and
# the src/ layout put it on sys.path.
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "tests.philosophy.convention.canonical.settings",
)

django.setup()

from django.core.management import call_command  # noqa: E402
from django.db import connection, transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from tests.philosophy import seed_data  # noqa: E402
from tests.philosophy.convention.canonical.models import (  # noqa: E402
    Customer,
    InventoryLevel,
    Notification,
    Order,
    OrderStatus,
    Product,
    PromoCode,
)


@pytest.fixture(scope="module")
def django_db_setup() -> None:
    """Create the schema once for the whole module."""
    with connection.schema_editor() as _editor:
        call_command("migrate", verbosity=0, interactive=False, run_syncdb=True)


@pytest.fixture
def seeded_db(django_db_setup) -> None:
    """Wipe and reseed the database around each test."""
    sid = transaction.savepoint()
    try:
        # Clear every table (order matters only for FK consistency)
        Notification.objects.all().delete()
        Order.objects.all().delete()
        InventoryLevel.objects.all().delete()
        PromoCode.objects.all().delete()
        Product.objects.all().delete()
        Customer.objects.all().delete()

        for c in seed_data.CUSTOMERS:
            Customer.objects.create(
                customer_id=c["customer_id"],
                name=c["name"],
                email=c["email"],
                standing=c["standing"],
                credit_limit=Decimal(str(c["credit_limit"])),
            )
        for p in seed_data.PRODUCTS:
            Product.objects.create(
                sku=p["sku"],
                name=p["name"],
                unit_price=Decimal(str(p["unit_price"])),
                max_per_order=int(p["max_per_order"]),  # type: ignore[arg-type]
                category=p["category"],
            )
        for level in seed_data.INVENTORY:
            InventoryLevel.objects.create(
                sku=level["sku"],
                on_hand=int(level["on_hand"]),  # type: ignore[arg-type]
                reserved=int(level["reserved"]),  # type: ignore[arg-type]
            )
        for promo in seed_data.PROMO_CODES:
            PromoCode.objects.create(
                code=promo["code"],
                percent_off=int(promo["percent_off"]),  # type: ignore[arg-type]
                expires_at=timezone.make_aware(datetime.fromisoformat(str(promo["expires_at"]))),
            )
        yield
    finally:
        transaction.savepoint_rollback(sid)


def _place(data: dict[str, Any]) -> Order:
    return Order.objects.place_order(
        customer_id=str(data["customer_id"]),
        line_items=list(data["line_items"]),  # type: ignore[arg-type]
        promo_code=(str(data["promo_code"]) if data.get("promo_code") is not None else None),
        shipping_address=str(data["shipping_address"]),
        order_id=str(data["order_id"]),
    )


def _assert_confirmed(case: dict[str, Any], order: Order) -> None:
    assert order.status == OrderStatus.CONFIRMED, (
        f"{case['name']}: expected confirmed, got {order.status} (reason: {order.rejection_reason})"
    )
    assert order.final_price == Decimal(str(case["expected_final_price"])), (
        f"{case['name']}: final price mismatch — "
        f"expected {case['expected_final_price']}, got {order.final_price}"
    )


def _assert_rejected(case: dict[str, Any], order: Order) -> None:
    assert order.status == OrderStatus.REJECTED, (
        f"{case['name']}: expected rejected, got {order.status}"
    )
    reason = order.rejection_reason
    assert reason, f"{case['name']}: rejected order must carry a reason"
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
def test_pipeline_matches_expected_outcome(case: dict[str, Any], seeded_db) -> None:
    order = _place(case["order"])  # type: ignore[arg-type]

    if case["expected_status"] == "confirmed":
        _assert_confirmed(case, order)
    elif case["expected_status"] == "rejected":
        _assert_rejected(case, order)
    else:
        pytest.fail(f"unknown expected_status in {case['name']}")

    assert Notification.objects.filter(order_id=case["order"]["order_id"]).exists(), (
        f"{case['name']}: outcome for {case['order']['order_id']} was not notified"
    )


def _order_dict(order_id: str, items: list[tuple[str, int]]) -> dict[str, Any]:
    return {
        "order_id": order_id,
        "customer_id": "C001",
        "line_items": [{"sku": sku, "quantity": qty} for sku, qty in items],
        "promo_code": None,
        "shipping_address": "123 Main St",
    }


def test_confirmed_order_decrements_available_inventory(seeded_db) -> None:
    """Seed stock for WIDGET-01 is 100; after 2-unit order confirms, 99 must fail."""
    first = _place(seed_data.TEST_ORDERS[0]["order"])  # type: ignore[arg-type]
    assert first.status == OrderStatus.CONFIRMED

    huge = _place(_order_dict("O-HUGE", [("WIDGET-01", 99)]))
    assert huge.status == OrderStatus.REJECTED, (
        "follow-up order should be rejected because the first order's "
        "reservation left only 98 available, not 99"
    )


def test_out_of_stock_order_does_not_partially_reserve(seeded_db) -> None:
    """Atomicity: a failed reservation must leave no line partially reserved."""
    mixed = _place(_order_dict("O-MIX", [("WIDGET-01", 5), ("EMPTY-01", 1)]))
    assert mixed.status == OrderStatus.REJECTED

    followup = _place(_order_dict("O-FOLLOW", [("WIDGET-01", 5)]))
    assert followup.status == OrderStatus.CONFIRMED


def test_every_model_is_registered_in_admin() -> None:
    """Rubric #7: admin is wired for every domain model.

    A Convention exemplar without admin registrations is not faithful
    — the admin is one of the highest-leverage features Django ships,
    and refusing it means refusing the framework's main offer.
    """
    from django.contrib import admin as admin_site

    # Force admin module import so @admin.register decorators run
    import tests.philosophy.convention.canonical.admin  # noqa: F401

    registered = set(admin_site.site._registry.keys())
    required = {
        Customer,
        Product,
        InventoryLevel,
        PromoCode,
        Order,
        Notification,
    }
    missing = required - registered
    assert not missing, (
        f"Convention exemplar failed rubric #7: these models are not "
        f"registered in admin: {sorted(m.__name__ for m in missing)}"
    )


def test_reversible_migration_exists() -> None:
    """Rubric #4: migrations exist for every schema change.

    The exemplar ships 0001_initial.py. A drift check (makemigrations
    --check) verifies that models.py and the migration are in sync —
    if a field is added without a matching migration, this test fails.
    """
    from io import StringIO

    out = StringIO()
    try:
        call_command(
            "makemigrations",
            "--check",
            "--dry-run",
            verbosity=0,
            stdout=out,
            stderr=out,
        )
    except SystemExit as exc:
        pytest.fail(
            f"Convention exemplar models.py and migrations are out of sync: {out.getvalue() or exc}"
        )
