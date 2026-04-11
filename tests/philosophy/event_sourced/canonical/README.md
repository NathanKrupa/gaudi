# Event-Sourced / CQRS — Reference Exemplar

**Canonical task:** Order processing pipeline ([docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md))
**Axiom sheet:** [docs/philosophy/event-sourced.md](../../../../docs/philosophy/event-sourced.md)
**Rubric score:** 10/10

The eighth and final reference implementation of the canonical
task, and the first built around the claim that the log is the
authoritative record of what the system is. Orders are streams of
past-tense events. State is a projection. The aggregate emits
facts rather than mutating rows. Replay is a test case.

---

## Running it

```bash
conda run -n Oversteward pytest tests/philosophy/event_sourced/ -v
```

Nineteen tests exercise the ten shared acceptance cases from the
seed data, plus two atomicity regressions, plus seven rubric-
enforcing tests that pin the architectural shape (frozen events,
pure aggregate, rebuild from log, time-travel, new-projection-
without-changing-write-side, intent-carrying names, placed-
first-in-stream). The seed data lives at
[`tests/philosophy/seed_data.py`](../../seed_data.py) and is
shared, unchanged, with every other school's implementation.

---

## Directory shape

```
canonical/
├── README.md       # this file
├── __init__.py
├── events.py       # 11 frozen dataclasses: OrderPlaced, LineItemAdded, ... × 6 rejections
├── event_store.py  # append-only in-process log with time-travel slice
├── aggregate.py    # place_order command handler (pure function, no mutation)
├── projections.py  # CurrentOrdersProjection + InventoryReservationsProjection + rebuild helpers
└── pipeline.py     # process_order entry point: command -> events -> store -> projections
```

Eleven event types, one command handler, two projections, one
event store, one entry point. The aggregate is a free function,
not a class — aggregates are consistency boundaries, not object
identities, and the event-sourced discipline is satisfied by a
pure function whose every invariant violation produces a named
rejection event.

---

## Rubric score against [event-sourced.md](../../../../docs/philosophy/event-sourced.md)

| # | Check | ✓/✗ | Evidence |
|---|---|---|---|
| 1 | Orders represented as a stream of past-tense events, not a mutable row | ✓ | The canonical record of an order is the sequence `OrderPlaced` → `LineItemAdded`* → `OrderPricingCalculated` → `InventoryReserved`* → `OrderConfirmed`, or (on any invariant violation) a single `OrderRejectedFor*` event. No mutable row exists anywhere in the codebase. `test_placed_event_is_always_first_in_success_stream` pins the shape. |
| 2 | Aggregate exposes commands that produce events; no setters | ✓ | The only public entry to the aggregate is `aggregate.place_order(command, …)`. It takes a `PlaceOrderCommand` (frozen) plus read-only state and returns a `tuple[Event, …]`. There are no setters and no instance attributes — the aggregate is a pure function because the aggregate identity is its consistency boundary, not its object identity. |
| 3 | Every state change is an event | ✓ | `test_aggregate_place_order_does_not_mutate_inputs` pins this: the aggregate must not mutate `on_hand`, the inventory projection, or any other input. All state transitions live in the events. |
| 4 | Events are frozen dataclasses | ✓ | Every event class in [`events.py`](events.py) is `@dataclass(frozen=True, slots=True)`. `test_events_are_frozen` attempts to reassign a field on a real event and asserts `FrozenInstanceError`. |
| 5 | At least one read-side projection exists | ✓ | Two projections exist: `CurrentOrdersProjection` (maps order_id to current state) and `InventoryReservationsProjection` (maps sku to total reserved quantity). Both live in [`projections.py`](projections.py) and are clearly separated from the write-side aggregate. |
| 6 | Projection rebuild is demonstrated | ✓ | `rebuild_current_orders(store)` and `rebuild_inventory(store)` in [`projections.py`](projections.py) iterate the full log from event zero and produce fresh projections. `test_projection_rebuild_matches_live_state` runs the entire acceptance suite, rebuilds both projections from scratch, and asserts the rebuilt state matches the live state field-by-field. |
| 7 | Event names capture intent, not just outcome | ✓ | Six distinct rejection event types name six specific business causes: `OrderRejectedForUnknownCustomer`, `OrderRejectedForCustomerStanding`, `OrderRejectedForUnknownProduct`, `OrderRejectedForQuantityExceeded`, `OrderRejectedForInsufficientInventory`, `OrderRejectedForCreditLimit`. No generic `OrderRejected` exists. `test_event_names_capture_intent_not_outcome` pins the property. |
| 8 | Aggregate invariants enforced at command time | ✓ | `aggregate.place_order` enforces every invariant (1) customer exists, (2) standing is good, (3) sku exists, (4) quantity ≤ max_per_order, (5) stock available, (6) credit limit respected — before emitting the success stream. A rejection at any step returns a tuple of exactly one rejection event and nothing else. |
| 9 | A new query use case is served by a new projection over the log | ✓ | `test_new_projection_can_be_added_without_writing_events` demonstrates this: an ad-hoc per-customer order-count query is answered inline by iterating `store.all_events()` without adding any event type or touching the aggregate. The flexibility is the point. |
| 10 | At least one time-travel query is demonstrated | ✓ | `projections.state_of_order_at(store, order_id, when)` replays every event whose `occurred_at <= when` into a fresh projection and returns the single row. `test_time_travel_query_returns_historical_state` places two orders at distinct timestamps and asserts that a query pinned to the earlier cutoff does not see the later order. |

**10/10.**

---

## The findings on this exemplar

Running `gaudi check` against this exemplar under `school =
event-sourced` (or any other school — the finding set is bit-
identical across every school) produces three kinds of findings,
each a legitimate universal cost of the discipline.

### Category A — SMELL-003 LongFunction (×4)

- `aggregate.place_order` is 181 lines. The function enforces six
  invariants inline and emits a named rejection event for each,
  then constructs the success-path event sequence. Extracting the
  six invariant checks into helper functions would split the
  reading of "what events does this command produce under what
  conditions?" across seven files and force the reader to chase
  flows instead of reading them in order. The axiom's rubric #8
  ("aggregate invariants enforced at command time") is more
  legible with them all in one place.
- `pipeline.process_order` is 53 lines. The length is honest
  plumbing: translate the dict to a command, invoke the
  aggregate, append events, update projections, derive the
  outcome. Every line is one of those five steps; splitting would
  obscure the flow.
- `pipeline._outcome_from_events` is 39 lines. The adapter
  between the event sequence and the shared outcome dict. This
  is the only place in the exemplar where a terminal event's
  type is pattern-matched into a dict shape; inlining it into
  process_order would make that function longer.
- `projections.CurrentOrdersProjection.apply` is 33 lines. The
  dispatch-on-event-type pattern the rubric #2 demands.

All four findings are accepted costs. SMELL-003 fires universally
and is not a scope decision.

### Category B — SMELL-004 LongParameterList (×2)

- `aggregate.place_order` has 8 parameters. Customers, products,
  on_hand, inventory_projection, promo_codes, shipping_fee, now,
  plus the command itself. Every one is read by the invariant
  checks; bundling them into a `WorldContext` value object would
  save a line at the call site and cost the reader the explicit
  dependency list.
- `pipeline.process_order` has 11 parameters, including both
  projections and every piece of the static world state. This is
  the honest wiring boundary: every caller provides exactly these
  things, and hiding them behind a context object would make the
  dependency harder to trace, not easier.

Accepted costs. Both SMELL-004 findings would disappear under a
"pipeline context" refactor, but that refactor would add a class
with no behavior — the exact shape the Event-Sourced axiom
refuses (rubric #2: commands, not getters on state-holder objects).

### Category C — STRUCT-021 MagicStrings (×6)

`'order_id'`, `'status'`, `'final_price'`, `'reservation_id'`,
`'rejection_reason'`, `'customer_id'` appear multiple times in
`projections.py` and `pipeline.py` because the acceptance
outcome is a plain dict shared across all exemplars. The
alternative is a `dataclass` for the outcome, which would diverge
from the outcome shape the other seven exemplars produce and
break the "same tests, same seed" contract.

---

## Scope posture and matrix rows

This exemplar joins `SCOPE_INVARIANT_EXEMPLARS` alongside
Pragmatic, Functional, and Resilient. Its finding set is bit-
identical across every valid school, including the ones whose
scope-tag decisions would shift a less careful exemplar's findings
(classical/convention scoping DOM-001, pragmatic/functional/
data-oriented scoping SMELL-014, unix scoping away ARCH-013 and
LOG-004). None of those rules fire because:

- **No OOP-specific rule fires.** Events are frozen dataclasses
  with zero methods. The aggregate is a free function, not a
  class. The event store and projections are three-method holder
  classes that no detector pattern-matches as single-method
  wrappers, large classes, middle-men, or pure-data classes with
  behavior elsewhere.
- **No stability rule fires.** The exemplar has no third-party
  HTTP or queue client calls, so the STAB-* family (timeouts,
  bulkheads, retries) has nothing to pattern-match against. This
  is the same property the Resilient exemplar exploits for the
  opposite reason.
- **No LOG-004 fires.** There are no print() calls. Logging, if
  it were added, would be structured and would not trip LOG-004
  (which scopes away from unix; irrelevant here).

What the matrix rows assert, under every school:

- **Required:** `SMELL-003`, `SMELL-004`, `STRUCT-021` — universal
  costs of the Event-Sourced discipline.
- **Forbidden:** the OOP-specific rules that presuppose classes
  with behavior — `SMELL-014`, `SMELL-018`, `SMELL-020`,
  `SMELL-022`, `SMELL-023`, `ARCH-002`, `DOM-001`. If any of
  these ever fires on this exemplar, the exemplar has grown a
  class it shouldn't have, or a scope filter broke.

---

## Comparison with the other exemplars

| Property | Classical | Pragmatic | Functional | Event-Sourced |
|---|---|---|---|---|
| Files | 8 across 4 layers | 1 | 3 | 6 |
| Public classes with behavior | 12 | 0 | 0 | 2 (store, 2 projections) |
| Frozen value types | 0 | 0 | 4 (records) | 11 (events) |
| Inheritance | 3 levels | 0 | 0 | 0 |
| Source of truth | aggregate row | dict | fresh copies | **event log** |
| Rebuild from primary data | N/A | N/A | N/A | every projection, tested |
| Time-travel query | impossible | impossible | impossible | **first-class** |

**The same ten acceptance tests pass against all four.** The
canonical task's invariants are enforced identically. What
differs is what the system *remembers*: Classical remembers the
current state of each order, Pragmatic remembers the in-memory
dicts, Functional remembers immutable record values, and
Event-Sourced remembers everything that ever happened. The
first three can answer "what is the order's state now?" with a
dict lookup; only Event-Sourced can answer "what was the order's
state at 14:22:03 on Tuesday?" without special infrastructure.

The trade-off is paid up front: Event-Sourced spends lines of
code on frozen event types, a store, projections, and a rebuild
path that no other exemplar needs. The axiom's §6 degenerate-
case section warns about paying that cost on a problem that does
not need it. The canonical task happens to be the right shape —
it has a clear history worth preserving (every rejection cause
is a business fact) and it makes the rubric's claims legible.

---

## Honest limitations

- **In-process, not durable.** The event store is a Python list.
  A production event-sourced system would use an append-only
  database (EventStoreDB, Kafka's compacted topics, a plain
  Postgres `events` table with a monotonic `global_seq` column).
  The axiom sheet explicitly refuses the infrastructure parody;
  this exemplar is small enough that the in-process list *is*
  the honest demonstration.
- **No eventual consistency.** Projections are updated
  synchronously after every append, so a caller that reads a
  projection after a write always sees the write. A real system
  would usually have a delay window, which adds correctness
  considerations the canonical task does not exercise.
- **Reservation ids are deterministic.** The other exemplars
  use a monotonic counter; this one derives the id from the
  order_id and first sku so replay produces the same ids. A
  real system would typically use UUIDs assigned at command
  time and stored on the event.
- **No cancellation flow.** The canonical task has no
  `cancel_order` command. Adding one would be a matter of
  defining `OrderCancelledByCustomer` / `OrderCancelledByFraud`
  / etc. and teaching the current-orders projection to apply
  them — no change to the aggregate's command handler for
  `place_order`, no change to the event store. That extensibility
  is the rubric #9 claim the exemplar was designed around.

---

## See also

- [docs/philosophy/event-sourced.md](../../../../docs/philosophy/event-sourced.md) — The axiom sheet and rubric.
- [docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md) — The canonical task specification.
- [tests/philosophy/functional/canonical/README.md](../../functional/canonical/README.md) — Event-sourcing's closest ally: events are immutable values, projections are folds.
- [tests/philosophy/classical/canonical/README.md](../../classical/canonical/README.md) — The school event-sourcing contradicts most sharply on aggregate mutation.
