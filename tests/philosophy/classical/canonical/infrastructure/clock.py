"""
Clock abstractions for services that need the current time.

The time source is infrastructure — it is a dependency a service
reaches outside itself for, and under Classical discipline every
such dependency is injected rather than fetched. Extracting Clock
into its own module keeps the pricing service free of concerns
other than pricing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class Clock(Protocol):
    """Provides the current time to services that depend on it."""

    def now(self) -> datetime: ...


class SystemClock:
    """A clock that returns the real system time."""

    def now(self) -> datetime:
        return datetime.now()


class FixedClock:
    """A clock that always returns a fixed time — for deterministic tests."""

    def __init__(self, fixed: datetime) -> None:
        self._fixed = fixed

    def now(self) -> datetime:
        return self._fixed
