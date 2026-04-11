"""
Reliability primitives: timeouts, bounded retry with backoff,
circuit breaker, idempotency keys.

These are the bricks. The pipeline stages use them to wrap every
call that crosses a trust boundary — which in this exemplar means
every call into the ``dependencies`` module, because those functions
stand in for the real external services (pricing catalog, inventory
DB, notification broker) that a production system would reach over
a network.

Refused temptations:

- **No unbounded retry.** Every retry loop has an explicit maximum
  attempt count; a retry without a bound is a self-directed
  denial-of-service attack waiting for the right failure.
- **No silent fallback.** A timeout is raised, not swallowed into a
  "safe default"; the caller chooses whether to degrade. Principle
  #13: the system must explain itself, including its failures.
- **No fixed-sleep retry.** Backoff is exponential, so retries do
  not pile onto a dependency that is already struggling.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, TypeVar

from tests.philosophy.resilient.canonical import config, telemetry

T = TypeVar("T")


class TimeoutExceeded(Exception):
    """Raised when a wrapped call exceeds its explicit timeout."""


class CircuitOpen(Exception):
    """Raised when a call is refused because the circuit breaker is open."""


def call_with_timeout(
    func: Callable[[], T],
    *,
    timeout_seconds: float,
    label: str,
) -> T:
    """Run ``func`` in a worker thread with an explicit wall-clock bound.

    The stdlib does not provide a portable thread-interruptible
    timeout, so a timeout that fires here abandons the worker rather
    than cancelling it. The abandoned thread will finish eventually
    and drop its result; the caller gets ``TimeoutExceeded`` and
    decides whether to retry. This is honest — a real remote call
    behaves the same way: the local socket abandons the read, the
    remote end may still complete and reply into the void.
    """
    # Copy the parent's context so the correlation ID (a ContextVar)
    # propagates into the worker — otherwise every log line emitted
    # from inside the wrapped call is untagged and an on-call engineer
    # loses the thread of the order through the telemetry.
    ctx = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(ctx.run, func)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeoutError as exc:
            telemetry.log(
                "WARN",
                "timeout_exceeded",
                label=label,
                timeout_seconds=timeout_seconds,
            )
            raise TimeoutExceeded(f"{label} exceeded {timeout_seconds}s timeout") from exc


def retry_with_backoff(
    func: Callable[[], T],
    *,
    label: str,
    max_attempts: int = config.MAX_RETRY_ATTEMPTS,
    initial_backoff: float = config.INITIAL_BACKOFF_SECONDS,
    multiplier: float = config.BACKOFF_MULTIPLIER,
    retry_on: tuple[type[BaseException], ...] = (TimeoutExceeded,),
) -> T:
    """Call ``func`` up to ``max_attempts`` times with exponential backoff.

    Retries only the exception types listed in ``retry_on`` so a
    logic error (a ``KeyError`` from unknown SKU, for example) does
    not get retried — retrying a deterministic failure is a waste
    of load with no upside.
    """
    backoff = initial_backoff
    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except retry_on as exc:
            telemetry.log(
                "WARN",
                "retry_attempt_failed",
                label=label,
                attempt=attempt,
                max_attempts=max_attempts,
                error=type(exc).__name__,
            )
            if attempt == max_attempts:
                raise
            time.sleep(backoff)
            backoff *= multiplier
    raise RuntimeError(f"retry_with_backoff[{label}] exited the loop without returning or raising")


class CircuitBreaker:
    """Nygard-style three-state circuit breaker.

    States:
      - CLOSED: calls pass through. Consecutive failures are counted.
        When ``failure_threshold`` is reached, the breaker OPENS.
      - OPEN: calls raise ``CircuitOpen`` immediately without
        invoking the protected callable. After ``cooldown_seconds``,
        the breaker moves to HALF_OPEN.
      - HALF_OPEN: the next call is allowed through. If it succeeds
        the breaker CLOSES; if it fails the breaker re-OPENS and
        the cooldown clock restarts.

    Principle #4: failure must be named. When the breaker opens,
    the event is logged at WARN with the breaker's label and the
    reason it tripped, so an on-call engineer tailing the logs can
    see which dependency is down without attaching a debugger.
    """

    def __init__(
        self,
        label: str,
        *,
        failure_threshold: int = config.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
        cooldown_seconds: float = config.CIRCUIT_BREAKER_COOLDOWN_SECONDS,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._label = label
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._now = now
        self._state: str = "CLOSED"
        self._consecutive_failures: int = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        return self._state

    def call(self, func: Callable[[], T]) -> T:
        self._maybe_half_open()
        if self._state == "OPEN":
            telemetry.log(
                "WARN",
                "circuit_call_refused",
                breaker=self._label,
                state=self._state,
            )
            raise CircuitOpen(f"{self._label} breaker open")

        try:
            result = func()
        except Exception:
            self._trip()
            raise
        if self._state == "HALF_OPEN":
            telemetry.log("INFO", "circuit_closed", breaker=self._label)
        self._state = "CLOSED"
        self._consecutive_failures = 0
        self._opened_at = None
        return result

    def _maybe_half_open(self) -> None:
        if self._state != "OPEN" or self._opened_at is None:
            return
        if self._now() - self._opened_at >= self._cooldown_seconds:
            self._state = "HALF_OPEN"
            telemetry.log("INFO", "circuit_half_open", breaker=self._label)

    def _trip(self) -> None:
        self._consecutive_failures += 1
        if self._state == "HALF_OPEN" or self._consecutive_failures >= self._failure_threshold:
            self._state = "OPEN"
            self._opened_at = self._now()
            telemetry.log(
                "WARN",
                "circuit_opened",
                breaker=self._label,
                consecutive_failures=self._consecutive_failures,
                cooldown_seconds=self._cooldown_seconds,
            )


def idempotency_key(order: dict[str, Any]) -> str:
    """Deterministic key for a state-mutating order operation.

    Derived from the order_id + canonical JSON of its line items. If
    the same order is replayed — because the caller retried after a
    timeout, because a message arrived twice, or because an operator
    replayed a log — the key is identical, and the downstream system
    can deduplicate.

    Catechism #6: at-least-once-with-idempotency is achievable under
    partitions; exactly-once is not.
    """
    canonical = json.dumps(
        {
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "line_items": sorted(order["line_items"], key=lambda li: str(li["sku"])),
            "promo_code": order.get("promo_code"),
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    return f"idem-{order['order_id']}-{digest}"
