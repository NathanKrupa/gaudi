# Event-Sourced / CQRS — Axiom Sheet

> *The log of events is the state. Current state is a projection, not a source.*

---

## 1. Prime axiom

> **The fundamental record of what a system is, is the ordered log of what
> has happened to it. Current state is a derived view over that log — one
> projection among many possible — and the system's design must treat the
> log as authoritative and the projections as replaceable.**

Conventional data modeling records outcomes: the order status is "cancelled."
Event-sourced modeling records causes: the order was cancelled because the
customer reached a fraud-check threshold at 14:22:03 on Tuesday. The first
model throws away the information that would have let an auditor, a
regulator, a future product manager, or a machine-learning model reconstruct
what the business actually did. The second preserves that information
permanently, at the cost of shifting where the complexity lives — and the
Event-Sourced school claims that shift is a bargain.

## 2. The rejected alternative

Event-sourced architecture refuses:

- **In-place mutation of aggregates.** An `order.status = "cancelled"`
  statement throws away the record of what the status was before, why it
  changed, and when. The cancellation is a *fact*; the update is a lie
  about the shape of that fact.
- **CRUD as the default persistence model for transactional systems.**
  Create-Read-Update-Delete records only the current state; the history
  is whatever the audit log happened to catch. Under Event-Sourcing, the
  audit log *is* the database, not an afterthought.
- **Losing intent by storing only outcomes.** `status_changed_from_X_to_Y`
  is weaker than `OrderCancelledByCustomer` because the latter names the
  actor and the cause. The former is a mechanical trace; the latter is a
  business fact.
- **Treating audit as an afterthought.** An audit system bolted onto a
  CRUD database answers "what does it look like now?" but cannot answer
  "what did we know at time T?" without heroic reconstruction. Event
  sourcing answers both natively.
- **Read-and-write models sharing the same schema.** CQRS separates the
  write side (commands producing events) from the read side (projections
  optimized for queries) because the two have different requirements and
  fighting that difference in a single schema produces a schema that
  serves neither well.
- **UPDATE statements on event-store tables.** An event, once written,
  is a historical fact. Rewriting it is rewriting history.
- **Projections that cannot be rebuilt from the log.** A projection that
  depends on state that is not in the event log is a projection whose
  correctness cannot be verified and whose bugs cannot be fixed by
  replay.

## 3. Canonical citations

- Young, Greg. "CQRS Documents." cqrs.wordpress.com, 2010. — The
  foundational essay collection on command-query responsibility
  separation and its relationship to event sourcing.
- Young, Greg. "Event Sourcing." GOTO Conference, 2014. — The canonical
  talk, with worked examples showing the shift from state-based to
  event-based thinking.
- Dahan, Udi. "Clarified CQRS." udidahan.com, 2009. — The clearest
  explanation of when CQRS pays off and when it is overkill, from one
  of the pattern's originators.
- Vernon, Vaughn. *Implementing Domain-Driven Design.* Addison-Wesley,
  2013. — Chapters 4 and 8 are the most accessible book-length
  treatment of event sourcing and aggregates working together.
- Kreps, Jay. "The Log: What every software engineer should know about
  real-time data's unifying abstraction." LinkedIn Engineering, 2013.
  — The durable-log perspective, which is the infrastructure spine
  event sourcing rides on at scale.
- Kleppmann, Martin. *Designing Data-Intensive Applications.* O'Reilly,
  2017. — Chapter 11, "Stream Processing," is the modern reference for
  log-based architectures and their consistency properties.
- Fowler, Martin. "Event Sourcing." martinfowler.com, 2005. — The first
  widely-read description of the pattern in the enterprise space.
- Evans, Eric. *Domain-Driven Design.* Addison-Wesley, 2003. — The
  aggregate concept that event sourcing relies on as its consistency
  boundary.

## 4. The catechism

Seven derived commitments:

1. **Events are facts, and facts are immutable.** An event happened; it
   cannot un-happen. Event types are frozen value objects. Storing an
   event is appending to a log; there is no such thing as "updating an
   event."
2. **Current state is a projection.** It is derived from the log, not
   stored as the source of truth. The log is authoritative; the
   projection is convenient.
3. **Write models and read models are separated.** Commands are handled
   by aggregates that enforce invariants and emit events. Queries are
   served by projections that have been optimized for reading. The two
   sides do not share a schema.
4. **Intent is captured, not just outcome.** Event names are past-tense
   and carry the business reason for the change: `OrderCancelledByCustomer`,
   `OrderCancelledByFraudCheck`, `OrderCancelledBySystemTimeout`. Three
   events, three causes, three meanings — not one event with a "reason"
   field that everyone ignores.
5. **Replay is cheap and legal.** Any projection can be rebuilt from
   scratch by replaying the event log from zero. This is not a disaster
   recovery capability; it is a normal operation, and the system is
   designed assuming it will be exercised.
6. **Time-travel is a first-class capability.** The system can answer
   "what was the state of order X at time T?" for any past T, because
   the log contains exactly the information needed to reconstruct it.
7. **Aggregates enforce invariants on the write side.** The aggregate
   is the consistency boundary; events that leave the aggregate are
   facts the rest of the system can trust without re-validation.

## 5. Rule shape this axiom generates

- **Forbid** — mutation of event instances after creation, UPDATE or
  DELETE statements against event-store tables, aggregate methods that
  return "updated selves" instead of emitting events, direct queries
  against read-side projections from the write side, projections that
  depend on state not in the event log, non-idempotent projection
  handlers, event names in present or imperative tense.
- **Require** — events as immutable value objects (frozen dataclasses
  or equivalent), append-only event stores, separate read-side
  projections for every distinct query use case, past-tense event
  names, idempotent projection handlers.
- **Prefer** — explicit event versioning strategies (upcasting,
  schema migration), event names that carry business intent, aggregate
  command methods that return events rather than mutating fields.

This axiom contributes a distinct slice of rules that sit awkwardly
inside any other school: the "no mutation on aggregates" rule is not
Functional (which forbids mutation everywhere), not Classical (which
permits aggregate state changes), and not Pragmatic (which would not
extract the event type at all until pressure arrived). Event sourcing
earns its place on the map because these rules *contradict* other
schools' rules without being subsumed by them.

## 6. The degenerate case

Every axiom has a failure mode. For Event-Sourced, the failure mode is
**event sourcing as fetish**.

- Every CRUD app contorted into an event log because a conference talk
  was persuasive. The team pays the full price of event-sourced
  infrastructure (projections, replay, eventual consistency, versioning)
  on a problem that would have been solved by a single UPDATE statement.
- Projection bugs discovered months later because the event is right but
  the current-state view has been wrong the whole time, and nobody
  rebuilt from the log often enough to notice. The log's authority is
  rhetorical; the projection is what the business actually reads.
- Eventual consistency used as an excuse for wrong answers. "The
  projection will catch up" becomes the team's standard response to any
  report that does not match expectations, until the report and the
  reality have diverged enough to hurt someone.
- A team that cannot answer a simple reporting question because every
  query requires writing a new projection and waiting for it to rebuild.
  The flexibility of "add projections retroactively" has become the
  rigidity of "we cannot answer ad-hoc questions."
- Storing events without ever reading them. The log as cargo cult: the
  team writes events because the pattern demands it, but the projections
  are all stale and the replay has never been tested, so the log is
  really just an expensive audit trail of questionable integrity.
- Event names that fail to capture intent: `OrderStatusChanged` as the
  only event type, with a `from` and `to` field. This is CRUD wearing
  an event costume. The whole point was to preserve intent; an event
  that does not preserve intent is an event in name only.

The test for event-sourcing-as-fetish: can the team demonstrate, with a
running example, the rebuild of a projection from scratch? If replay
has never been exercised, the log's authority is hypothetical, and
hypothetical authority is not authority.

## 7. Exemplar temptation

When writing the Event-Sourced implementation of the canonical task,
the exemplar must navigate two opposite temptations:

- **The CRUD shortcut.** It will be tempting to model the order as a
  row in a table with a `status` field and an `audit_log` column that
  stores a JSON blob of changes. The Event-Sourced exemplar must refuse
  — the events must be first-class records in an append-only store, the
  aggregate must emit them rather than mutate the row, and the current
  state must be a projection that can be rebuilt from the log.
- **The infrastructure parody.** It will also be tempting to pull in
  Kafka, EventStoreDB, or a full-weight CQRS framework to demonstrate
  "realism." The exemplar must refuse this too. The infrastructure
  should be the simplest honest thing that demonstrates the discipline:
  an in-process append-only list of events, a few projection
  dictionaries built by replay, and a handful of functions that show
  the command → event → projection flow. Kafka is a deployment
  detail; event sourcing is a modeling discipline.

The faithful Event-Sourced exemplar is the one where: orders are
represented as a stream of past-tense events (`OrderPlaced`,
`LineItemAdded`, `PricingCalculated`, `InventoryReserved`,
`OrderConfirmed`, `OrderCancelledByCustomer`); the order aggregate
exposes command methods that emit events rather than mutate fields;
every state change is an event; projections exist for current-state
queries and can be rebuilt by replay; the exemplar demonstrates at
least one replay in a test or script; and at least one time-travel
query is shown.

## 8. Rubric — how to recognize a faithful Event-Sourced fixture

- [ ] **Orders are represented as a stream of past-tense events**, not
      as a mutable row. The event stream is the canonical representation.
- [ ] **The order aggregate exposes commands** (e.g., `place_order`,
      `cancel_order`) that produce events; no setters, no direct field
      mutation from outside the aggregate.
- [ ] **Every state change is expressed as an event.** No UPDATE-in-place
      on the aggregate, no "just this one field" exceptions.
- [ ] **Events are frozen dataclasses** (or the language equivalent)
      with no methods that return mutated copies and no fields that can
      be reassigned after construction.
- [ ] **At least one read-side projection exists** that materializes
      current state for querying, and is clearly distinct from the
      write-side aggregate.
- [ ] **Projection rebuild is demonstrated** in the exemplar — a test
      or script that tears down the projection, replays the log from
      zero, and produces the same current state.
- [ ] **Event names capture intent, not just outcome.** Not
      `OrderStatusChanged`, but `OrderCancelledByCustomer` /
      `OrderCancelledByFraudCheck` / `OrderConfirmed`.
- [ ] **Aggregate invariants are enforced at command time**, before the
      event is emitted. A command that would violate an invariant
      (cancelling a shipped order) is rejected by the aggregate, not
      caught by a downstream check.
- [ ] **A new query use case can be added by writing a new projection**
      without changing the write side. The exemplar documents how this
      would work, or demonstrates it with a second projection.
- [ ] **At least one time-travel query is demonstrated** — "what was the
      state of order X at time T?" — showing that the history is real,
      not ornamental.

Ten out of ten is Event-Sourced. Eight or nine is a draft. Seven or
fewer is CRUD with an audit log.

---

## See also

- [docs/philosophy/functional.md](functional.md) — Event-sourcing and
  functional programming are natural allies: events are immutable
  values, projections are folds over a sequence, and the aggregate's
  command handler is a pure function from `(state, command)` to events.
  Much of the discipline translates cleanly between the two schools.
- [docs/philosophy/classical.md](classical.md) — Event-sourcing
  contradicts Classical DDD's default of in-place aggregate mutation.
  Both schools care deeply about aggregates and invariants, but they
  disagree about how aggregates should record what happens to them.
- [docs/philosophy/resilient.md](resilient.md) — The append-only log is
  the backbone of many resilience patterns (replay, reprocessing,
  dead-letter handling). The two schools share infrastructure even
  when they are optimizing for different properties.
- [docs/principles.md](../principles.md) — This school's contribution
  to the universal core is narrower than most: it mostly adds rules
  rather than reshaping existing ones, because its central claim
  (the log is authoritative) is genuinely novel and does not sit
  comfortably inside any other school's frame.
