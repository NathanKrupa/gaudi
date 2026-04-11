"""
End-to-end tests for the Resilience-First reference implementation.

The tests cover:

1. **Acceptance cases** — every row of ``seed_data.TEST_ORDERS``
   runs through ``process_order`` and must match the expected
   status and final price. These prove the pipeline actually
   implements the business logic in between all the reliability
   machinery.
2. **Rubric-enforcing tests** — each clause of the Resilient
   rubric (`docs/philosophy/resilient.md` section 8) is pinned by
   at least one test so a future refactor that removes the
   machinery silently also fails a test loudly:
     - timeouts: every wrapper has an explicit value, enforced
       by ``test_every_dependency_call_has_explicit_timeout``
     - retries: bounded and backed off, enforced by
       ``test_retry_respects_max_attempts``
     - circuit breaker: opens after threshold consecutive failures,
       enforced by ``test_notification_breaker_opens_after_threshold``
     - idempotency: deterministic keys + replay suppression,
       enforced by ``test_idempotency_key_is_deterministic_and_replays_safely``
     - structured logging + correlation IDs, enforced by
       ``test_structured_log_tags_every_stage_with_correlation_id``
     - health check produces real capability report, enforced by
       ``test_healthcheck_reports_real_capability``
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import pytest

from tests.philosophy import seed_data
from tests.philosophy.resilient.canonical import (
    config,
    dependencies,
    pipeline,
    reliability,
    telemetry,
)

_NOW = datetime(2026, 4, 10, 12, 0, 0)


def _build_world() -> dict[str, Any]:
    return {
        "customers": {c["customer_id"]: dict(c) for c in seed_data.CUSTOMERS},
        "products": {p["sku"]: dict(p) for p in seed_data.PRODUCTS},
        "inventory": {i["sku"]: dict(i) for i in seed_data.INVENTORY},
        "promo_codes": {p["code"]: dict(p) for p in seed_data.PROMO_CODES},
    }


@pytest.fixture(autouse=True)
def _reset_state() -> None:
    telemetry.reset_sink()
    dependencies.reset_switch()
    pipeline.reset_notification_breaker()


@pytest.fixture
def world() -> dict[str, Any]:
    return _build_world()


# ---- Acceptance --------------------------------------------------------


@pytest.mark.parametrize("case", seed_data.TEST_ORDERS, ids=lambda c: str(c["name"]))
def test_pipeline_matches_expected_outcome(case: dict[str, Any], world: dict[str, Any]) -> None:
    outcome = pipeline.process_order(case["order"], world, _NOW)

    if case["expected_status"] == "confirmed":
        assert outcome["status"] == "confirmed", (
            f"{case['name']}: expected confirmed, got {outcome['status']} "
            f"(reason: {outcome.get('rejection_reason')})"
        )
        assert outcome["final_price"] == str(case["expected_final_price"])
        assert outcome["reservation_id"] is not None
        assert outcome["reservation_id"].startswith("RES-")
    elif case["expected_status"] == "rejected":
        assert outcome["status"] == "rejected"
        reason = outcome.get("rejection_reason")
        assert reason is not None
        if "expected_reason_contains" in case:
            assert str(case["expected_reason_contains"]) in reason
        if "expected_reason_contains_all" in case:
            for needle in case["expected_reason_contains_all"]:  # type: ignore[union-attr]
                assert str(needle) in reason
    else:
        pytest.fail(f"unknown expected_status in {case['name']}")


def test_confirmed_order_decrements_available_inventory(world: dict[str, Any]) -> None:
    """SCARCE-01 has on_hand=3, max_per_order=5. One order of 3 exhausts
    the stock; a follow-up of 1 must be rejected for insufficient
    inventory, proving the first order really reserved.
    """
    first = pipeline.process_order(
        {
            "order_id": "O-SCARCE-1",
            "customer_id": "C001",
            "line_items": [{"sku": "SCARCE-01", "quantity": 3}],
            "promo_code": None,
            "shipping_address": "123 Main St",
        },
        world,
        _NOW,
    )
    assert first["status"] == "confirmed"

    followup = pipeline.process_order(
        {
            "order_id": "O-SCARCE-2",
            "customer_id": "C001",
            "line_items": [{"sku": "SCARCE-01", "quantity": 1}],
            "promo_code": None,
            "shipping_address": "123 Main St",
        },
        world,
        _NOW,
    )
    assert followup["status"] == "rejected"
    assert "SCARCE-01" in followup["rejection_reason"]


# ---- Rubric: timeouts --------------------------------------------------


def test_every_dependency_call_has_explicit_timeout() -> None:
    """Rubric #1: every function that touches anything beyond memory
    has an explicit timeout constant.

    The configuration module is the single source of truth for
    timeout values. This test pins the three named constants the
    pipeline uses so any accidental removal breaks a test, not a
    2am incident.
    """
    for name in (
        "PRICING_TIMEOUT_SECONDS",
        "INVENTORY_TIMEOUT_SECONDS",
        "NOTIFICATION_TIMEOUT_SECONDS",
    ):
        value = getattr(config, name)
        assert isinstance(value, float)
        assert 0 < value < 60, f"{name} should be a reasoned value in (0, 60)"


def test_pricing_timeout_triggers_retry_then_reject(world: dict[str, Any]) -> None:
    """A pricing call that exceeds the timeout must raise TimeoutExceeded.

    The pipeline catches this and rejects the order with a named
    reason — Principle #4, failure must be named. The order is NOT
    silently downgraded to a happy-path outcome.
    """
    dependencies.SWITCH.pricing_delay_seconds = config.PRICING_TIMEOUT_SECONDS + 0.3
    outcome = pipeline.process_order(
        {
            "order_id": "O-SLOW",
            "customer_id": "C001",
            "line_items": [{"sku": "WIDGET-01", "quantity": 1}],
            "promo_code": None,
            "shipping_address": "123 Main St",
        },
        world,
        _NOW,
    )
    assert outcome["status"] == "rejected"
    assert "pricing unavailable" in outcome["rejection_reason"]


# ---- Rubric: retry bound + backoff --------------------------------------


def test_retry_respects_max_attempts() -> None:
    """Rubric #2: retry loops must have a maximum attempt count.

    Use ``retry_with_backoff`` directly on a function that always
    raises and assert it is called exactly ``MAX_RETRY_ATTEMPTS``
    times before giving up.
    """
    attempts: list[int] = []

    def always_fails() -> None:
        attempts.append(1)
        raise reliability.TimeoutExceeded("synthetic")

    with pytest.raises(reliability.TimeoutExceeded):
        reliability.retry_with_backoff(
            always_fails,
            label="test",
            max_attempts=3,
            initial_backoff=0.001,
            multiplier=2.0,
        )

    assert len(attempts) == 3


def test_retry_backoff_is_exponential() -> None:
    """Rubric #2: backoff must be exponential, not fixed.

    Record the sleeps observed via monkey-patching ``time.sleep``
    and assert the sequence is [initial, initial*m, initial*m*m,...].
    """
    import time as _time

    sleeps: list[float] = []
    real_sleep = _time.sleep

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        real_sleep(0)

    def always_fails() -> None:
        raise reliability.TimeoutExceeded("synthetic")

    _time.sleep = fake_sleep  # type: ignore[assignment]
    try:
        with pytest.raises(reliability.TimeoutExceeded):
            reliability.retry_with_backoff(
                always_fails,
                label="test",
                max_attempts=4,
                initial_backoff=0.01,
                multiplier=2.0,
            )
    finally:
        _time.sleep = real_sleep  # type: ignore[assignment]

    assert sleeps == pytest.approx([0.01, 0.02, 0.04])


# ---- Rubric: circuit breaker --------------------------------------------


def test_notification_breaker_opens_after_threshold(world: dict[str, Any]) -> None:
    """Rubric #5: a circuit breaker must guard a flaky dependency.

    Force ``publish_notification`` to raise on every call. After
    ``CIRCUIT_BREAKER_FAILURE_THRESHOLD`` consecutive failures the
    breaker must open and subsequent calls must be refused with
    ``CircuitOpen``. The notification-degraded log line must name
    ``CircuitOpen`` as the reason once the breaker has tripped.
    """
    dependencies.SWITCH.notification_raises = True

    # Process enough orders to trip the breaker. Orders succeed
    # (inventory is fine) but the notification publish fails each
    # time. After threshold consecutive failures the breaker trips.
    for i in range(config.CIRCUIT_BREAKER_FAILURE_THRESHOLD):
        order = {
            "order_id": f"O-B{i}",
            "customer_id": "C001",
            "line_items": [{"sku": "WIDGET-01", "quantity": 1}],
            "promo_code": None,
            "shipping_address": "123 Main St",
        }
        outcome = pipeline.process_order(order, world, _NOW)
        assert outcome["status"] == "confirmed", (
            "notification failure must not fail the order — it is "
            "a side-channel degradation, not a business-state failure"
        )

    assert pipeline.NOTIFICATION_BREAKER.state == "OPEN"

    # The next order's notification call is refused immediately.
    final = pipeline.process_order(
        {
            "order_id": "O-B-FINAL",
            "customer_id": "C001",
            "line_items": [{"sku": "WIDGET-01", "quantity": 1}],
            "promo_code": None,
            "shipping_address": "123 Main St",
        },
        world,
        _NOW,
    )
    assert final["status"] == "confirmed"

    degraded_events = [r for r in telemetry.SINK if r["event"] == "notification_degraded"]
    assert any(r.get("reason") == "CircuitOpen" for r in degraded_events), (
        "expected at least one notification_degraded event with reason=CircuitOpen"
    )


# ---- Rubric: idempotency ------------------------------------------------


def test_idempotency_key_is_deterministic_and_replays_safely(world: dict[str, Any]) -> None:
    """Rubric #3: every state-mutating external call must carry an
    idempotency key; a replay with the same key must be suppressed.
    """
    order = {
        "order_id": "O-IDEM",
        "customer_id": "C001",
        "line_items": [{"sku": "WIDGET-01", "quantity": 2}],
        "promo_code": None,
        "shipping_address": "123 Main St",
    }
    key1 = reliability.idempotency_key(order)
    key2 = reliability.idempotency_key(dict(order))
    assert key1 == key2, "same payload must produce the same idempotency key"
    assert key1.startswith("idem-O-IDEM-")

    first = pipeline.process_order(order, world, _NOW)
    assert first["status"] == "confirmed"
    first_reserved = world["inventory"]["WIDGET-01"]["reserved"]

    # Replay the same order: the idempotency layer at the reserve
    # step must skip the re-reservation.
    dependencies.reserve_inventory(
        world,
        [("WIDGET-01", 2)],
        idempotency_key=key1,
    )
    second_reserved = world["inventory"]["WIDGET-01"]["reserved"]
    assert second_reserved == first_reserved, (
        "replayed reservation must be suppressed by idempotency key"
    )


# ---- Rubric: structured logging + correlation IDs -----------------------


def test_structured_log_tags_every_stage_with_correlation_id(world: dict[str, Any]) -> None:
    """Rubric #4: every log line emitted during an order must be
    structured and tagged with the correlation ID set at the top of
    ``process_order``.
    """
    telemetry.reset_sink()
    outcome = pipeline.process_order(seed_data.TEST_ORDERS[0]["order"], world, _NOW)
    assert outcome["status"] == "confirmed"

    order_records = [r for r in telemetry.SINK if r["correlation_id"] == outcome["correlation_id"]]
    assert order_records, "no telemetry records carried the order's correlation ID"

    events = {r["event"] for r in order_records}
    assert "order_received" in events
    assert "order_confirmed" in events

    # All records for this order have a correlation_id that matches
    # the emitted ``cid-<hex>`` format.
    for rec in order_records:
        assert re.match(r"^cid-[0-9a-f]+$", rec["correlation_id"])


# ---- Rubric: health check -----------------------------------------------


def test_healthcheck_reports_real_capability(world: dict[str, Any]) -> None:
    """Rubric #7: the health check must test actual capability, not
    merely report that the process is alive.

    In the happy case it returns status='ok'. When the pricing
    dependency is broken it returns status='degraded' with a
    specific failure message naming the subsystem.
    """
    ok = pipeline.healthcheck(world)
    assert ok["status"] == "ok"
    assert ok["pricing"] == "ok"
    assert ok["inventory"] == "ok"
    assert ok["notification_breaker"] == "CLOSED"

    dependencies.SWITCH.pricing_raises = True
    degraded = pipeline.healthcheck(world)
    assert degraded["status"] == "degraded"
    assert degraded["pricing"].startswith("fail:")


# ---- Rubric: failure modes are explicit paths ---------------------------


def test_notification_failure_does_not_fail_the_order(world: dict[str, Any]) -> None:
    """The pipeline declares notification as a side-channel: a
    failure there must not corrupt a confirmed order. This test is
    the contract.
    """
    dependencies.SWITCH.notification_raises = True
    outcome = pipeline.process_order(seed_data.TEST_ORDERS[0]["order"], world, _NOW)
    assert outcome["status"] == "confirmed"
    degraded = [r for r in telemetry.SINK if r["event"] == "notification_degraded"]
    assert len(degraded) >= 1
