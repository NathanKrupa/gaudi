"""
End-to-end tests for the Unix reference implementation.

Two flavours of tests run against the same shared seed data:

1. **In-process unit tests** call ``validate_one`` / ``price_one`` /
   ``reserve_one`` / ``notification_record`` directly. Fast, easy
   to debug, and sufficient to cover every acceptance criterion.
2. **Subprocess pipeline tests** build a real shell-ish pipeline
   via Python's ``subprocess`` module: ``validate | price |
   reserve | notify``. This is what rubric check #10 demands —
   proof that the scripts actually compose as independent
   programs and that a shell one-liner would produce the same
   result the in-process tests observe.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from tests.philosophy import seed_data
from tests.philosophy.unix.canonical import notify, price, reserve, validate

_NOW = datetime(2026, 4, 10, 12, 0, 0)


def _build_world() -> dict[str, Any]:
    return {
        "customers": {c["customer_id"]: dict(c) for c in seed_data.CUSTOMERS},
        "products": {p["sku"]: dict(p) for p in seed_data.PRODUCTS},
        "inventory": {i["sku"]: dict(i) for i in seed_data.INVENTORY},
        "promo_codes": {p["code"]: dict(p) for p in seed_data.PROMO_CODES},
    }


@pytest.fixture
def world() -> dict[str, Any]:
    return _build_world()


def _run_in_process(order: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    """Run all four stages on one order and return the final result."""
    import itertools

    counter = itertools.count(world.get("_reservation_counter", 1))

    after_validate = validate.validate_one(order, world)
    after_price = price.price_one(after_validate, world, _NOW, Decimal(seed_data.SHIPPING_FEE))
    after_reserve = reserve.reserve_one(after_price, world, counter)
    return after_reserve


@pytest.mark.parametrize("case", seed_data.TEST_ORDERS, ids=lambda c: str(c["name"]))
def test_pipeline_matches_expected_outcome(case: dict[str, Any], world: dict[str, Any]) -> None:
    outcome = _run_in_process(case["order"], world)

    if case["expected_status"] == "confirmed":
        assert outcome["_status"] == "confirmed", (
            f"{case['name']}: expected confirmed, got {outcome['_status']} "
            f"(reason: {outcome.get('_rejection_reason')})"
        )
        assert outcome["_final_price"] == str(case["expected_final_price"]), (
            f"{case['name']}: final price mismatch — expected "
            f"{case['expected_final_price']}, got {outcome['_final_price']}"
        )
        assert outcome.get("_reservation_id") is not None
    elif case["expected_status"] == "rejected":
        assert outcome["_status"] == "rejected"
        reason = outcome.get("_rejection_reason")
        assert reason is not None
        if "expected_reason_contains" in case:
            assert str(case["expected_reason_contains"]) in reason
        if "expected_reason_contains_all" in case:
            for needle in case["expected_reason_contains_all"]:  # type: ignore[union-attr]
                assert str(needle) in reason
    else:
        pytest.fail(f"unknown expected_status in {case['name']}")


def test_confirmed_order_decrements_available_inventory(
    world: dict[str, Any],
) -> None:
    """Mutating the shared world in-process persists reservations."""
    import itertools

    counter = itertools.count(1)
    first_order = seed_data.TEST_ORDERS[0]["order"]
    after_validate = validate.validate_one(first_order, world)
    after_price = price.price_one(after_validate, world, _NOW, Decimal(seed_data.SHIPPING_FEE))
    first = reserve.reserve_one(after_price, world, counter)
    assert first["_status"] == "confirmed"

    huge = {
        "order_id": "O-HUGE",
        "customer_id": "C001",
        "line_items": [{"sku": "WIDGET-01", "quantity": 99}],
        "promo_code": None,
        "shipping_address": "123 Main St",
    }
    after_validate = validate.validate_one(huge, world)
    after_price = price.price_one(after_validate, world, _NOW, Decimal(seed_data.SHIPPING_FEE))
    second = reserve.reserve_one(after_price, world, counter)
    assert second["_status"] == "rejected", (
        "follow-up order should be rejected because the first order's "
        "reservation left only 98 available, not 99"
    )


def test_out_of_stock_order_does_not_partially_reserve(
    world: dict[str, Any],
) -> None:
    """A failed reservation must leave no line partially reserved."""
    import itertools

    counter = itertools.count(1)
    mixed = {
        "order_id": "O-MIX",
        "customer_id": "C001",
        "line_items": [
            {"sku": "WIDGET-01", "quantity": 5},
            {"sku": "EMPTY-01", "quantity": 1},
        ],
        "promo_code": None,
        "shipping_address": "123 Main St",
    }
    after_validate = validate.validate_one(mixed, world)
    after_price = price.price_one(after_validate, world, _NOW, Decimal(seed_data.SHIPPING_FEE))
    rejected = reserve.reserve_one(after_price, world, counter)
    assert rejected["_status"] == "rejected"

    followup = {
        "order_id": "O-FOLLOW",
        "customer_id": "C001",
        "line_items": [{"sku": "WIDGET-01", "quantity": 5}],
        "promo_code": None,
        "shipping_address": "123 Main St",
    }
    after_validate = validate.validate_one(followup, world)
    after_price = price.price_one(after_validate, world, _NOW, Decimal(seed_data.SHIPPING_FEE))
    confirmed = reserve.reserve_one(after_price, world, counter)
    assert confirmed["_status"] == "confirmed", (
        "follow-up order must still succeed — the rejected mixed "
        "order must not have partially reserved WIDGET-01"
    )


def test_subprocess_pipeline_composes_via_stdio(world: dict[str, Any]) -> None:
    """The rubric's teeth: validate | price | reserve | notify really pipes.

    This test invokes each stage as a subprocess, connected with
    real pipes, and reads the terminal stdout. If any stage fails
    to parse stdin, write stdout, or handle its CLI flags, this
    test fails loudly.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        world_path = Path(tmpdir) / "world.json"
        log_path = Path(tmpdir) / "notifications.jsonl"
        world_path.write_text(json.dumps(world), encoding="utf-8")

        # Pick two orders: a confirmed happy-path and a rejection.
        orders_input = "\n".join(
            [
                json.dumps(seed_data.TEST_ORDERS[0]["order"]),  # happy path
                json.dumps(seed_data.TEST_ORDERS[3]["order"]),  # customer on hold
            ]
        )

        stage1 = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tests.philosophy.unix.canonical.validate",
                "--world",
                str(world_path),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        stage2 = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tests.philosophy.unix.canonical.price",
                "--world",
                str(world_path),
                "--shipping-fee",
                seed_data.SHIPPING_FEE,
                "--now",
                _NOW.isoformat(),
            ],
            stdin=stage1.stdout,
            stdout=subprocess.PIPE,
        )
        stage3 = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tests.philosophy.unix.canonical.reserve",
                "--world",
                str(world_path),
            ],
            stdin=stage2.stdout,
            stdout=subprocess.PIPE,
        )
        stage4 = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "tests.philosophy.unix.canonical.notify",
                "--log",
                str(log_path),
            ],
            stdin=stage3.stdout,
            stdout=subprocess.PIPE,
        )

        # Close the intermediate pipe read-ends in this process so the
        # subprocesses own them exclusively.
        assert stage1.stdout is not None
        stage1.stdout.close()
        assert stage2.stdout is not None
        stage2.stdout.close()
        assert stage3.stdout is not None
        stage3.stdout.close()

        assert stage1.stdin is not None
        stage1.stdin.write(orders_input.encode("utf-8"))
        stage1.stdin.close()

        out, _ = stage4.communicate(timeout=30)
        stage1.wait(timeout=10)
        stage2.wait(timeout=10)
        stage3.wait(timeout=10)

        for stage, name in [
            (stage1, "validate"),
            (stage2, "price"),
            (stage3, "reserve"),
            (stage4, "notify"),
        ]:
            assert stage.returncode == 0, f"stage {name} exited with {stage.returncode}"

        lines = [ln for ln in out.decode("utf-8").splitlines() if ln.strip()]
        assert len(lines) == 2, f"expected 2 output orders, got {len(lines)}"

        first = json.loads(lines[0])
        second = json.loads(lines[1])
        assert first["_status"] == "confirmed"
        assert first.get("_reservation_id", "").startswith("RES-")
        assert second["_status"] == "rejected"
        assert "standing" in second["_rejection_reason"]

        # The notification log should contain exactly two records.
        log_contents = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(log_contents) == 2

        # world.json should reflect the first order's reservation.
        updated_world = json.loads(world_path.read_text(encoding="utf-8"))
        assert updated_world["inventory"]["WIDGET-01"]["reserved"] == 2


def test_every_stage_has_a_cli_main() -> None:
    """Rubric #6: every module must be invocable as a standalone program."""
    for module in (validate, price, reserve, notify):
        assert hasattr(module, "main"), f"{module.__name__} must expose a main() entry point"
        assert callable(module.main)


def test_every_stage_has_no_classes() -> None:
    """Rubric #9: classes exist only where a module could not replace them.

    Under the Unix discipline, module namespaces hold functions;
    classes are reserved for cases where no module could do the
    job. The order pipeline stages have no such cases, so zero
    classes is the correct count.
    """
    import ast
    import pathlib

    canonical_dir = pathlib.Path(__file__).parent / "canonical"
    for py_file in canonical_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert not classes, (
            f"{py_file.name} contains class(es) {[c.name for c in classes]} "
            f"— the Unix discipline uses modules, not classes"
        )
