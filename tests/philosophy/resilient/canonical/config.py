"""
Named constants for every timeout, retry count, backoff parameter,
and circuit-breaker threshold in the Resilient exemplar.

Rubric #6: timeouts, retry counts, and circuit-breaker thresholds
must be named constants, not magic numbers scattered through the
code. Every knob lives here so an operator tuning the pipeline for
a real production incident knows exactly where to look.

The comments alongside each constant record the *reasoned value* —
why 0.5 seconds and not 5, why three retries and not ten. A timeout
without a reason is a guess in a costume.
"""

from __future__ import annotations

from decimal import Decimal

# ---- Timeouts ---------------------------------------------------------------

# Pricing service is in-memory in this exemplar; in a real system it
# would be an HTTP call to a catalog service. 500ms is "slow enough
# to tolerate a GC pause but fast enough that the caller notices the
# stall."
PRICING_TIMEOUT_SECONDS: float = 0.5

# Inventory calls are reads against the in-memory world in this
# exemplar; a real implementation would hit Postgres. 300ms is the
# 99th-percentile target for a single indexed read under load.
INVENTORY_TIMEOUT_SECONDS: float = 0.3

# Notification is fire-and-forget to a message broker in real
# deployments. 1 second is generous because the broker's own
# durability SLA is longer than a synchronous read.
NOTIFICATION_TIMEOUT_SECONDS: float = 1.0

# ---- Retries ----------------------------------------------------------------

# Three attempts is Nygard's rule of thumb: one retry covers a
# transient blip, two covers a failing instance being pulled out of
# rotation, three is the point past which retries stop helping and
# start amplifying the outage.
MAX_RETRY_ATTEMPTS: int = 3

# 50ms initial backoff, doubling on each retry (50, 100, 200). The
# total added latency on a triple-retry is ~350ms — inside the
# pricing timeout window by a comfortable margin.
INITIAL_BACKOFF_SECONDS: float = 0.05
BACKOFF_MULTIPLIER: float = 2.0

# ---- Circuit breaker --------------------------------------------------------

# Five consecutive failures before we open the breaker. Lower than
# this and one flaky instance during a deploy trips us; higher and
# we cascade too many failed calls before tripping.
CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5

# 10 seconds of cooldown before the breaker moves to HALF_OPEN. Long
# enough for a dependency's autoscaler to add capacity, short enough
# that we are not shedding load for half a minute.
CIRCUIT_BREAKER_COOLDOWN_SECONDS: float = 10.0

# ---- Domain -----------------------------------------------------------------

SHIPPING_FEE: Decimal = Decimal("5.00")
