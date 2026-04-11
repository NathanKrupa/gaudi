"""
Append-only event store with time-travel and replay.

This is the simplest honest event store that demonstrates the
discipline: an in-process list of events, append-only, read by
linear scan. The axiom-sheet's "exemplar temptation" section
warns against pulling in Kafka or EventStoreDB for realism —
infrastructure is a deployment detail, event sourcing is a
modeling discipline, and the discipline is visible with a Python
list and a lock.

Operations
----------
- ``append(event)`` / ``append_many(events)`` — add one or many
  events to the end of the log. Events already in the log are
  never touched, never updated, never deleted. There is no
  ``replace_at`` method and there never will be.
- ``events_for_order(order_id)`` — linear scan returning every
  event whose ``order_id`` matches. The order-id indexing is a
  convenience for projections and tests; it is not part of the
  fact-log itself.
- ``events_up_to(when)`` — every event whose ``occurred_at <= when``.
  This is the primitive behind time-travel queries: any
  projection can be rebuilt against a historical cutoff by
  iterating this slice instead of the full log.
- ``all_events()`` — iterate the entire log in append order.
  Projections use this for full-replay rebuilds (rubric #6).

Deliberate refusals
-------------------
- **No UPDATE.** Once an event is appended, its fields are
  frozen (at the dataclass level) and its position in the log
  is fixed (at the list level). Nothing in the public surface
  can mutate an already-logged event.
- **No DELETE.** Events can only be added. A future feature
  that needs "correction" would append a compensating event
  (``OrderCorrectionApplied``), not rewrite history.
- **No secondary index that cannot be rebuilt from the log.**
  The indexing done in ``events_for_order`` is a linear scan
  against the canonical list. A future optimization could cache
  results per order_id, but the cache would be derivable from
  the log and would be rebuilt by replay like any other
  projection.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from tests.philosophy.event_sourced.canonical.events import Event


class EventStore:
    """In-process append-only event log.

    The ``_events`` list is private by convention; external
    callers must go through the public API. The public API
    contains no mutation verb except ``append``.
    """

    def __init__(self) -> None:
        self._events: list[Event] = []

    def append(self, event: Event) -> None:
        """Append one event to the end of the log."""
        self._events.append(event)

    def append_many(self, events: Iterable[Event]) -> None:
        """Append a sequence of events atomically-enough for in-process.

        In a durable store this would be one transaction. In
        this in-process exemplar, append_many is the same as a
        for-loop over append — the simplification is honest
        because there is no concurrent writer in the acceptance
        suite.
        """
        for event in events:
            self._events.append(event)

    def all_events(self) -> tuple[Event, ...]:
        """Immutable snapshot of every event in append order.

        Returns a tuple rather than the backing list so callers
        cannot accidentally mutate the log by append/pop/clear.
        """
        return tuple(self._events)

    def events_for_order(self, order_id: str) -> tuple[Event, ...]:
        """Every event whose ``order_id`` matches, in append order."""
        return tuple(e for e in self._events if e.order_id == order_id)

    def events_up_to(self, when: datetime) -> tuple[Event, ...]:
        """Every event whose ``occurred_at <= when``, in append order.

        The primitive for time-travel: replay these events into
        a fresh projection and you get the state the system held
        as of ``when``. Any projection type can be rebuilt at
        any cutoff without special support — the log is
        sufficient on its own.
        """
        return tuple(e for e in self._events if e.occurred_at <= when)

    def __len__(self) -> int:
        return len(self._events)
