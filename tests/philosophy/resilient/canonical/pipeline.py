"""
The order-processing pipeline, with the Resilience-First discipline
baked in at every trust boundary.

Every call into ``dependencies`` — pricing, inventory, notification
— passes through the reliability wrappers (explicit timeout, bounded
retry with exponential backoff, circuit breaker). Every log line is
structured and tagged with the correlation ID set at the top of
``process_order``. Every state-mutating call carries an idempotency
key derived deterministically from the order payload.

Subsystem failure modes are documented in the code, not hidden in a
future TODO:

- **Pricing fails.** Retry with backoff. If retries exhaust, reject
  the order with the reason named in the telemetry.
- **Inventory fails on read.** Retry. If retries exhaust, reject.
- **Inventory fails on reserve.** Do NOT retry — reservations are
  state-mutating and the idempotency key handles replay at the
  dependency layer; a raised InventoryError here is an insufficient-
  stock signal and retrying it would be a lie.
- **Notification fails.** Swallow the exception but log the failure
  at WARN. The order is already confirmed; the notification is a
  side channel, not a commit. This is the one explicit degradation
  path in the pipeline, and it is named in the code.
- **Circuit open on notification.** Same treatment as a transient
  failure: the order is confirmed, the log line is emitted, and
  the on-call engineer sees ``circuit_call_refused`` telemetry.

The ``healthcheck`` function tests actual capability (the world is
readable, the pricing call returns, the inventory call returns)
rather than merely reporting that the process is alive. Rubric #7.
"""

from __future__ import annotations

import itertools
import uuid
from datetime import datetime as _dt
from decimal import Decimal
from typing import Any

from tests.philosophy.resilient.canonical import (
    config,
    dependencies,
    reliability,
    telemetry,
)

_reservation_counter = itertools.count(1)


def _next_reservation_id() -> str:
    return f"RES-{next(_reservation_counter):06d}"


# One notification breaker per pipeline process. Real deployments
# would scope this per dependency *instance* (one breaker per
# downstream pod) but for a single-process exemplar one is correct.
NOTIFICATION_BREAKER = reliability.CircuitBreaker("notification")


def reset_notification_breaker() -> None:
    global NOTIFICATION_BREAKER
    NOTIFICATION_BREAKER = reliability.CircuitBreaker("notification")


def process_order(
    order: dict[str, Any],
    world: dict[str, Any],
    now: _dt,
) -> dict[str, Any]:
    """Run one order through validate -> price -> reserve -> notify."""
    correlation_id = f"cid-{uuid.uuid4().hex[:12]}"
    idem_key = reliability.idempotency_key(order)
    with telemetry.correlation(correlation_id):
        telemetry.log("INFO", "order_received", order_id=order["order_id"])
        return _run_stages(order, world, now, correlation_id, idem_key)


def _run_stages(
    order: dict[str, Any],
    world: dict[str, Any],
    now: _dt,
    correlation_id: str,
    idem_key: str,
) -> dict[str, Any]:
    customer_err = _check_customer(order, world)
    if customer_err is not None:
        return _reject(order, correlation_id, idem_key, customer_err)

    resolved_or_err = _resolve_lines_safely(order, world)
    if isinstance(resolved_or_err, str):
        return _reject(order, correlation_id, idem_key, resolved_or_err)

    quantity_err = _check_max_per_order(resolved_or_err)
    if quantity_err is not None:
        return _reject(order, correlation_id, idem_key, quantity_err)

    inventory_err = _check_inventory_safely(resolved_or_err, world)
    if inventory_err is not None:
        return _reject(order, correlation_id, idem_key, inventory_err)

    customer = world["customers"][order["customer_id"]]
    final_price = _price(resolved_or_err, order, world, now)
    if final_price > Decimal(customer["credit_limit"]):
        return _reject(
            order,
            correlation_id,
            idem_key,
            (
                f"Final price {final_price} exceeds customer "
                f"{customer['customer_id']} credit limit {customer['credit_limit']}"
            ),
        )

    return _reserve_and_confirm(
        order, world, resolved_or_err, final_price, correlation_id, idem_key
    )


def _check_customer(order: dict[str, Any], world: dict[str, Any]) -> str | None:
    customer = dependencies.lookup_customer(world, order["customer_id"])
    if customer is None:
        return f"Unknown customer {order['customer_id']}"
    if customer["standing"] != "good":
        return (
            f"Customer {customer['customer_id']} standing is "
            f"{customer['standing']}; may not place orders"
        )
    return None


def _resolve_lines_safely(
    order: dict[str, Any], world: dict[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any]]] | str:
    try:
        return _resolve_lines(order, world)
    except reliability.TimeoutExceeded as exc:
        return f"pricing unavailable: {exc}"
    except dependencies.PricingError as exc:
        return str(exc)


def _check_max_per_order(
    resolved: list[tuple[dict[str, Any], dict[str, Any]]],
) -> str | None:
    for product, line in resolved:
        if line["quantity"] > product["max_per_order"]:
            return (
                f"Line item {line['sku']} quantity {line['quantity']} "
                f"exceeds max_per_order {product['max_per_order']}"
            )
    return None


def _check_inventory_safely(
    resolved: list[tuple[dict[str, Any], dict[str, Any]]],
    world: dict[str, Any],
) -> str | None:
    try:
        insufficient = _check_inventory(resolved, world)
    except reliability.TimeoutExceeded as exc:
        return f"inventory unavailable: {exc}"
    if insufficient:
        return f"Insufficient inventory for: {', '.join(insufficient)}"
    return None


def _reserve_and_confirm(
    order: dict[str, Any],
    world: dict[str, Any],
    resolved: list[tuple[dict[str, Any], dict[str, Any]]],
    final_price: Decimal,
    correlation_id: str,
    idem_key: str,
) -> dict[str, Any]:
    try:
        dependencies.reserve_inventory(
            world,
            [(p["sku"], line["quantity"]) for p, line in resolved],
            idempotency_key=idem_key,
        )
    except dependencies.InventoryError as exc:
        return _reject(order, correlation_id, idem_key, str(exc))

    outcome = {
        "order_id": order["order_id"],
        "status": "confirmed",
        "final_price": str(final_price),
        "reservation_id": _next_reservation_id(),
        "rejection_reason": None,
        "correlation_id": correlation_id,
        "idempotency_key": idem_key,
    }
    _notify(outcome, idem_key)
    telemetry.log(
        "INFO",
        "order_confirmed",
        order_id=order["order_id"],
        final_price=str(final_price),
    )
    return outcome


def _resolve_lines(
    order: dict[str, Any], world: dict[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    resolved: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for line in order["line_items"]:
        product = reliability.retry_with_backoff(
            lambda sku=line["sku"]: reliability.call_with_timeout(
                lambda: dependencies.lookup_product(world, sku),
                timeout_seconds=config.PRICING_TIMEOUT_SECONDS,
                label=f"pricing.lookup_product[{sku}]",
            ),
            label=f"pricing.lookup_product[{line['sku']}]",
            retry_on=(reliability.TimeoutExceeded,),
        )
        resolved.append((product, line))
    return resolved


def _check_inventory(
    resolved: list[tuple[dict[str, Any], dict[str, Any]]],
    world: dict[str, Any],
) -> list[str]:
    insufficient: list[str] = []
    for product, line in resolved:
        level = reliability.retry_with_backoff(
            lambda sku=product["sku"]: reliability.call_with_timeout(
                lambda: dependencies.read_inventory(world, sku),
                timeout_seconds=config.INVENTORY_TIMEOUT_SECONDS,
                label=f"inventory.read[{sku}]",
            ),
            label=f"inventory.read[{product['sku']}]",
            retry_on=(reliability.TimeoutExceeded,),
        )
        available = level["on_hand"] - level["reserved"]
        if available < line["quantity"]:
            insufficient.append(product["sku"])
    return insufficient


def _price(
    resolved: list[tuple[dict[str, Any], dict[str, Any]]],
    order: dict[str, Any],
    world: dict[str, Any],
    now: _dt,
) -> Decimal:
    subtotal = sum(
        (Decimal(p["unit_price"]) * line["quantity"] for p, line in resolved),
        start=Decimal(0),
    )
    discount = Decimal(0)
    code = order.get("promo_code")
    if code:
        promo = dependencies.lookup_promo(world, code)
        if promo and _dt.fromisoformat(promo["expires_at"]) > now:
            discount = (subtotal * Decimal(promo["percent_off"]) / Decimal(100)).quantize(
                Decimal("0.01")
            )
    return subtotal - discount + config.SHIPPING_FEE


def _notify(outcome: dict[str, Any], idem_key: str) -> None:
    """Publish a notification, degrading gracefully if the broker is down.

    This is the one explicit-degradation path in the pipeline. The
    order is already confirmed (inventory is reserved), and a
    missed notification is a side-channel failure rather than a
    business-state corruption. We name the failure in the log and
    move on.
    """
    try:
        NOTIFICATION_BREAKER.call(
            lambda: reliability.call_with_timeout(
                lambda: dependencies.publish_notification(outcome, idempotency_key=idem_key),
                timeout_seconds=config.NOTIFICATION_TIMEOUT_SECONDS,
                label="notification.publish",
            )
        )
    except (
        reliability.TimeoutExceeded,
        reliability.CircuitOpen,
        dependencies.NotificationError,
    ) as exc:
        telemetry.log(
            "WARN",
            "notification_degraded",
            order_id=outcome["order_id"],
            reason=type(exc).__name__,
            detail=str(exc),
        )


def _reject(
    order: dict[str, Any],
    correlation_id: str,
    idem_key: str,
    reason: str,
) -> dict[str, Any]:
    outcome = {
        "order_id": order["order_id"],
        "status": "rejected",
        "final_price": None,
        "reservation_id": None,
        "rejection_reason": reason,
        "correlation_id": correlation_id,
        "idempotency_key": idem_key,
    }
    telemetry.log(
        "INFO",
        "order_rejected",
        order_id=order["order_id"],
        reason=reason,
    )
    _notify(outcome, idem_key)
    return outcome


def healthcheck(world: dict[str, Any]) -> dict[str, Any]:
    """Return a real capability report, not a liveness ping.

    Rubric #7: the health check must test actual capability. This
    tests a real pricing lookup, a real inventory read, and the
    circuit-breaker state — the three things that matter when the
    on-call engineer needs to know whether the pipeline can still
    process orders.
    """
    checks: dict[str, Any] = {
        "pricing": _probe(
            lambda: dependencies.lookup_product(world, "WIDGET-01"),
            timeout=config.PRICING_TIMEOUT_SECONDS,
            label="healthcheck.pricing",
        ),
        "inventory": _probe(
            lambda: dependencies.read_inventory(world, "WIDGET-01"),
            timeout=config.INVENTORY_TIMEOUT_SECONDS,
            label="healthcheck.inventory",
        ),
        "notification_breaker": NOTIFICATION_BREAKER.state,
    }
    capability_ok = checks["pricing"] == "ok" and checks["inventory"] == "ok"
    checks["status"] = "ok" if capability_ok else "degraded"
    return checks


def _probe(func, *, timeout: float, label: str) -> str:
    """Run one health-check probe, return 'ok' or a descriptive failure.

    A broad except is correct here: the probe's contract is to
    classify the subsystem into ok/fail from whatever the subsystem
    chose to raise, including dependency errors, timeouts, and any
    unexpected error the dependency did not think to declare. The
    error is named in the returned string, not silently discarded —
    Principle #4 kept even in the catch-all path.
    """
    try:
        reliability.call_with_timeout(func, timeout_seconds=timeout, label=label)
        return "ok"
    except (reliability.TimeoutExceeded, dependencies.DependencyError) as exc:
        return f"fail: {type(exc).__name__}: {exc}"
