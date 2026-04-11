"""
In-process stand-ins for the external dependencies a real Resilient
pipeline would reach over a network.

Each function here represents a trust boundary. In production the
``pricing`` call would be an HTTP request to a catalog service; the
``inventory`` call would be a Postgres transaction; the ``notify``
call would be a message-broker publish. The pipeline code does not
know or care — it invokes them through the ``reliability`` wrappers
(timeout + retry + circuit breaker), and their in-process nature
does not weaken the rubric because the machinery is real.

The ``FlakySwitch`` class exists so tests can deterministically
force specific dependencies to time out or raise. It is not used by
the production pipeline path (the happy-path acceptance tests run
with an all-healthy switch) but the circuit-breaker test and the
retry-bound test both drive it. A real deployment has chaos
engineering tooling doing the equivalent; here the switch is the
cheapest thing that proves the machinery really runs.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from tests.philosophy.resilient.canonical import telemetry


class DependencyError(Exception):
    """Base class for every dependency-layer failure.

    A shared base lets callers catch one type when they do not care
    which specific subsystem failed — for example the health check
    reports any of these as a degraded state.
    """


class PricingError(DependencyError):
    """Raised when the pricing catalog is unreachable or unhealthy."""


class InventoryError(DependencyError):
    """Raised when the inventory store is unreachable or unhealthy."""


class NotificationError(DependencyError):
    """Raised when the notification broker is unreachable."""


@dataclass
class FlakySwitch:
    """Controls whether each dependency is currently 'healthy' or not.

    Tests manipulate this to force timeouts / raise from specific
    subsystems. The happy-path pipeline never touches it; the
    ``test_circuit_breaker_opens_after_threshold`` test does.
    """

    pricing_delay_seconds: float = 0.0
    inventory_delay_seconds: float = 0.0
    notification_raises: bool = False
    pricing_raises: bool = False


SWITCH = FlakySwitch()


def reset_switch() -> None:
    SWITCH.pricing_delay_seconds = 0.0
    SWITCH.inventory_delay_seconds = 0.0
    SWITCH.notification_raises = False
    SWITCH.pricing_raises = False


def lookup_product(world: dict[str, Any], sku: str) -> dict[str, Any]:
    """Pricing catalog lookup.

    Real version: HTTP GET /catalog/{sku}. Here: a dict lookup
    delayed by the flaky-switch knob so tests can deterministically
    force a timeout.
    """
    if SWITCH.pricing_delay_seconds > 0:
        time.sleep(SWITCH.pricing_delay_seconds)
    if SWITCH.pricing_raises:
        raise PricingError(f"pricing catalog unhealthy for {sku}")
    product = world["products"].get(sku)
    if product is None:
        raise PricingError(f"unknown product: {sku}")
    telemetry.log("DEBUG", "pricing_lookup_ok", sku=sku)
    return product


def read_inventory(world: dict[str, Any], sku: str) -> dict[str, int]:
    """Inventory read for one SKU.

    Real version: SELECT on_hand, reserved FROM inventory WHERE sku=$1.
    """
    if SWITCH.inventory_delay_seconds > 0:
        time.sleep(SWITCH.inventory_delay_seconds)
    level = world["inventory"].get(sku)
    if level is None:
        raise InventoryError(f"inventory row missing for {sku}")
    return {"on_hand": int(level["on_hand"]), "reserved": int(level["reserved"])}


def reserve_inventory(
    world: dict[str, Any],
    reservations: list[tuple[str, int]],
    idempotency_key: str,
) -> None:
    """Atomically reserve every line in ``reservations``.

    Real version: a transaction that does SELECT ... FOR UPDATE on
    each row, checks availability, and UPDATEs the reserved column.
    The idempotency key is persisted with the transaction so a
    replay of the same reservation returns the existing result
    instead of double-charging.

    Here we mutate the in-process world dict atomically (under the
    GIL, a single-threaded mutation is atomic by construction) and
    store the idempotency key in a side table.
    """
    seen_keys = world.setdefault("_idempotency_seen", {})
    if idempotency_key in seen_keys:
        telemetry.log(
            "INFO",
            "idempotent_replay_skipped",
            idempotency_key=idempotency_key,
        )
        return
    for sku, quantity in reservations:
        level = world["inventory"][sku]
        available = level["on_hand"] - level["reserved"]
        if available < quantity:
            raise InventoryError(f"insufficient stock for {sku}: need {quantity}, have {available}")
    for sku, quantity in reservations:
        world["inventory"][sku]["reserved"] += quantity
    seen_keys[idempotency_key] = True


def publish_notification(
    outcome: dict[str, Any],
    *,
    idempotency_key: str,
) -> None:
    """Fire-and-forget notification publish.

    Real version: an async enqueue onto a durable message broker
    (Kafka, SQS, NATS). Here: append to a world-local log. The
    idempotency key is logged so a consumer can deduplicate.
    """
    if SWITCH.notification_raises:
        raise NotificationError("notification broker unreachable")
    telemetry.log(
        "INFO",
        "notification_published",
        order_id=outcome["order_id"],
        status=outcome["status"],
        idempotency_key=idempotency_key,
    )


def lookup_customer(world: dict[str, Any], customer_id: str) -> dict[str, Any] | None:
    """Read-only customer lookup. Fast enough not to need retry."""
    return world["customers"].get(customer_id)


def lookup_promo(world: dict[str, Any], code: str) -> dict[str, Any] | None:
    """Read-only promo lookup."""
    return world["promo_codes"].get(code)


def decimal_price(raw: str) -> Decimal:
    return Decimal(raw)
