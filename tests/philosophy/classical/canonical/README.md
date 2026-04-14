# Classical / Structural — Reference Exemplar

**Canonical task:** Order processing pipeline ([docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md))
**Axiom sheet:** [docs/philosophy/classical.md](../../../../docs/philosophy/classical.md)
**Rubric score:** 10/10

This is the first reference implementation of the canonical task. It
demonstrates what an order-processing pipeline looks like when built
faithfully under Classical / Structural architectural discipline.

---

## Running it

The exemplar is ordinary Python that lives under `tests/philosophy/`.
Its tests are collected by the project's pytest run:

```bash
conda run -n Oversteward pytest tests/philosophy/classical/ -v
```

Twelve tests exercise every acceptance criterion from the canonical
task: happy path, valid promo, expired promo, customer on hold, banned
customer, over-quantity line item, exceeds credit limit, out of stock,
multiple unfillable lines (all named), unknown product, atomic
reservation consumption, and atomic non-partial reservation on
failure.

The seed data lives at [`tests/philosophy/seed_data.py`](../../seed_data.py)
and is shared, unchanged, with every other school's implementation.

---

## Package layout

```
canonical/
├── domain/              # inner: pure value objects, zero infra imports
│   └── models.py
├── infrastructure/      # inner: Protocols + in-memory adapters
│   ├── clock.py
│   └── repositories.py
├── services/            # middle: orchestrated business operations
│   ├── notification.py
│   ├── pricing.py
│   ├── reservation.py
│   └── validation.py
└── pipeline.py          # outer: composition root + OrderPipeline
```

Every arrow in the import graph points inward:

- `pipeline.py` imports from `services/`, `infrastructure/`, `domain/`
- `services/*.py` imports from `infrastructure/`, `domain/`
- `infrastructure/*.py` imports from `domain/`
- `domain/models.py` imports from nothing in this package

The domain kernel has zero infrastructure imports: no `logging`,
no `sqlite3`, no `requests`, no `os.getenv`, no clock. It would
survive a total rewrite of every storage and network dependency
without a line changing.

---

## Rubric score against [classical.md](../../../../docs/philosophy/classical.md)

| # | Check | ✓/✗ | Evidence |
|---|---|---|---|
| 1 | Dependency direction is diagrammable and strictly inward | ✓ | See layout above. No arrow reverses. |
| 2 | At least one boundary crossed via an interface hiding real complexity | ✓ | The four `Repository` Protocols in `infrastructure/repositories.py` hide "where the data is stored." A real database implementation is a one-file swap. |
| 3 | At least one named pattern used meaningfully | ✓ | **Repository** (Fowler PEAA). Not a decoration — the Protocol lets services depend on an interface while the composition root chooses the concrete implementation. |
| 4 | Domain model has zero infrastructure imports | ✓ | `domain/models.py` imports only `dataclasses`, `datetime`, `decimal`, `enum`. Nothing else. |
| 5 | Dependencies passed, not fetched (constructor injection) | ✓ | Every service receives its collaborators in `__init__`. No service calls `os.getenv`, no module-level singletons, no service locator. |
| 6 | Every class has a responsibility statable in one sentence without "and" | ✓ | `ValidationService` "decides whether an order can proceed to pricing." `PricingService` "computes the final price of a validated order." `ReservationService` "atomically reserves inventory for a validated order." `NotificationService` "delegates order-outcome notification to the configured sender." `OrderPipeline` "orchestrates an order through the four processing stages to a terminal outcome." |
| 7 | Top-level package layout readably describes the system | ✓ | A first-time reader seeing `domain/`, `infrastructure/`, `services/`, `pipeline.py` can predict what the system does and where each concern lives. |
| 8 | Refuses the procedural shortcut | ✓ | The code does not inline validation, pricing, reservation, and notification into one 80-line `process_order()` function, even though that would be shorter. The refusal is the point: separation of concerns earns its line count in clarity for the reader. |
| 9 | Refuses the pattern-worship shortcut | ✓ | Three refusals are visible: (a) no `Money` value object — plain `Decimal` carries monetary amounts because there is no multi-currency requirement; (b) no `PricingStrategy` hierarchy — `PricingService` is a concrete class with one pricing policy; (c) no `_check_credit` helper method on `OrderPipeline` — inlined into `process()` because the extraction was not hiding nameable complexity. Each refusal is documented in its module docstring. |
| 10 | All public APIs are type-annotated | ✓ | Every function, method, and dataclass field carries a type annotation. `mypy --strict` would be a next step. |

**10/10.**

---

## Notes on the gaudí findings

Running `gaudi check` against this exemplar at the project level produces
twelve findings, which fall into three categories. The categorization
itself is the forcing-function evidence for the Phase 1 engine change
that [docs/rule-sources.md](../../../../docs/rule-sources.md)
(Philosophy Scope Audit section) exists to justify.

### Category A — audit-validating false positives (SMELL-014, ×6)

**`SMELL-014 LazyElement`** fires on every `InMemory*Repository`,
`ReservationIdGenerator`, `SystemClock`, and `FixedClock` in the
exemplar. Each is a small single-method class wrapping one concrete
behavior. The rule says "consider inlining"; the Classical discipline
says "no — these classes exist to implement the Repository Protocol,
and inlining them would destroy the abstraction boundary."

The audit in [docs/rule-sources.md](../../../../docs/rule-sources.md)
already tags `SMELL-014` as scoped to `{pragmatic, unix, functional,
data-oriented}` — explicitly **not** Classical. **These six findings
are exactly what the audit predicted would be false positives when the
rule runs against a faithful Classical exemplar.**

This is the single clearest piece of evidence for Phase 1 (the
`Rule.philosophy_scope` engine change). When the engine respects
philosophy scope, these six findings disappear on this exemplar and
continue to fire correctly on Pragmatic or Unix exemplars where
single-method wrapper classes would actually indicate overengineering.

### Category B — detector precision issues (×4)

Four findings are caused by detector heuristics rather than
philosophical disagreement:

- **`SMELL-007 DivergentChange` (×3)** on `OrderPipeline`,
  `PricingService`, and `ValidationService`. Each of these classes has
  a single responsibility, but each has multiple methods serving that
  responsibility, and the detector's heuristic appears to count
  distinct method names as "reasons to change." Further splitting
  would be pattern-worship (rubric #9), so the exemplar refuses to
  fix this. A tighter detection rule is the appropriate remedy.
- **`SMELL-023 RefusedBequest` (×1)** on the `CustomerRepository`
  Protocol. Protocols are not inheritance; a Protocol class cannot
  "refuse a bequest" because there is no parent implementation to
  inherit from. This is a detector that hasn't learned about PEP 544
  structural subtyping.

These are good issues to file — they improve detection precision —
but they do not invalidate the exemplar's rubric score.

### Category C — genuine findings the exemplar could address (×2)

Two `STRUCT-021 MagicStrings` findings remain in `test_canonical.py`:
the strings `'name'` (9 occurrences) and `'C001'` (3 occurrences)
both appear multiple times. Extracting them as constants would
silence the rule but would also hurt readability — `'name'` is the
key of a test-case metadata dict, and `'C001'` is the customer id
that the test data happens to use. The exemplar leaves them in place
as a deliberate trade-off: readability over magic-string abstinence
in test code. A faithful Classical exemplar under the audit should
probably tag `STRUCT-021` as scoped-away-from-test-code specifically.

---

## Comparison notes for future implementations

When the Pragmatic exemplar lands, the expected diff is:

- Pragmatic will inline the services into a single flat `process_order()`
  function until the Rule of Three forces extraction. Where Classical
  has four service classes, Pragmatic will have four function calls
  inside one function.
- Pragmatic will not introduce the Repository Protocol — it will use
  the in-memory data structures directly until a second backend appears.
  This is exactly the thin-layer refusal that [pragmatic.md](../../../../docs/philosophy/pragmatic.md)
  catechism #1 ("YAGNI is sacred") demands.
- Pragmatic will probably score **fewer** SMELL-014 findings because
  the classes in question do not exist.

When the Functional exemplar lands, the expected diff is:

- No classes at all in the domain core, or only frozen-dataclass records.
- Services become modules of pure functions; the pipeline becomes a
  composition of those functions via `pipe`/`compose`.
- Errors are returned as `Result`-style tagged unions, not raised as
  exceptions. Several existing tests would need small adjustments to
  read the error branch.

When the Event-Sourced exemplar lands, the diff is largest: `Order`
becomes an event stream, the aggregate emits `OrderPlaced`,
`PricingCalculated`, `InventoryReserved`, `OrderConfirmed`, and
current state is a projection rebuilt from the log. The same twelve
tests pass; the internal representation is radically different.

Each of these differences is *what the schools disagree about*, and
the Classical exemplar is the anchor against which those disagreements
become visible.

---

## See also

- [docs/philosophy/classical.md](../../../../docs/philosophy/classical.md) — The axiom sheet.
- [docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md) — The canonical task specification.
- [docs/rule-sources.md](../../../../docs/rule-sources.md) — The rule audit, including the scope tag for SMELL-014.
- [docs/principles.md](../../../../docs/principles.md) — The universal core this exemplar satisfies.
