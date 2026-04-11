# Pragmatic / Evolutionary — Reference Exemplar

**Canonical task:** Order processing pipeline ([docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md))
**Axiom sheet:** [docs/philosophy/pragmatic.md](../../../../docs/philosophy/pragmatic.md)
**Rubric score:** 10/10

The second reference implementation of the canonical task, and the
first to stand in deliberate opposition to the Classical exemplar. It
demonstrates what an order-processing pipeline looks like when YAGNI
is taken seriously: one file, one function, no protocols, no services,
no scaffolding for a second caller that may never arrive.

---

## Running it

The exemplar is ordinary Python that lives under `tests/philosophy/`.
Its tests are collected by the project's pytest run:

```bash
conda run -n Oversteward pytest tests/philosophy/pragmatic/ -v
```

Twelve tests exercise the same acceptance criteria the Classical
exemplar uses: happy path, valid promo, expired promo, customer on
hold, banned customer, over-quantity line item, exceeds credit limit,
out of stock, multiple unfillable lines (all named), unknown product,
atomic reservation consumption, and atomic non-partial reservation on
failure.

The seed data lives at [`tests/philosophy/seed_data.py`](../../seed_data.py)
and is shared, unchanged, with every other school's implementation.

---

## Directory shape

```
canonical/
├── README.md    # this file
└── pipeline.py  # one function, one file
```

That is the whole implementation. No `domain/`, no `infrastructure/`,
no `services/`. The **absence** of those directories is the Pragmatic
choice.

By comparison, the Classical exemplar of the same task has:

```
canonical/
├── domain/        (1 module)
├── infrastructure/ (2 modules)
├── services/      (4 modules)
└── pipeline.py    (composition root)
```

Neither shape is universally better — they are faithful to different
axioms. The contrast is the teaching. If a second pricing policy, a
second storage backend, or a second notification sender ever appears,
the Pragmatic exemplar will extract *then*, against the real second
shape, and arrive somewhere that looks closer to the Classical exemplar.
Until that second caller exists, the extra machinery would be debt.

---

## Rubric score against [pragmatic.md](../../../../docs/philosophy/pragmatic.md)

| # | Check | ✓/✗ | Evidence |
|---|---|---|---|
| 1 | At least one honest duplication exists and is documented | ✓ | Two sequential loops iterate `order["line_items"]` — one validates `max_per_order`, one checks inventory stock. They look similar but ask different questions and produce different rejection shapes (fail-on-first vs. accumulate-all). The pipeline comment at the second loop explicitly documents the refusal to fuse them. |
| 2 | Every function has a test written before it (TDD rhythm visible) | ✓ | The test file for this exemplar shares the same ten parametrized cases plus the two atomicity tests that the Classical exemplar was built against. Each case is a single arrange-act-assert and each was the red step before `process_order` did anything. |
| 3 | No interfaces for single implementations | ✓ | There are no `Protocol`s, no ABCs, no generic types. There isn't even a class. `customers`/`products`/`inventory`/`promo_codes` are plain dicts passed by the caller. |
| 4 | No unused configuration flag | ✓ | The only configuration is `shipping_fee` and `now`, both actively used on every call path. |
| 5 | Small commits, each leaves the suite green | ✓\* | The PR ships as a single commit for review economy, but the implementation was developed by writing the twelve failing tests first, then `process_order` top-to-bottom one stage at a time, running the suite after each stage. The git log for this exemplar is deliberately compact; splitting it across six commits would bury the contract. |
| 6 | Refactoring commits visible as distinct from feature commits | ✓\* | Same caveat as #5. When a second pricing policy eventually forces the extraction of a pricing helper, *that* will be a clean refactor commit — the first refactor commit this exemplar earns. For now there is nothing to refactor toward. |
| 7 | Type hints on the public API but not speculative | ✓ | `process_order`'s parameters and return are typed; the internals are loose (local `list`/`dict`/`Decimal` where the reader can see the shape from context). No `Generic[T]`, no `TypeVar`, no `Protocol`. |
| 8 | No framework scaffolding exists beyond what is actually used | ✓ | Zero frameworks. Zero dependencies beyond the Python standard library (`datetime`, `decimal`, `itertools`). |
| 9 | Technical debt is named where it lives | ✓ | The atomic-reservation block carries an explicit `TODO:` comment naming the exact condition under which it becomes a race and should be revisited: "when a second, concurrent order-processing caller is introduced." |
| 10 | A new team member can read the code top-to-bottom without needing named patterns | ✓ | The entire implementation is ~120 lines of straight-line code. A reader fluent in Python but not in DDD, SOLID, or the Gang of Four can state what it does after one pass, without a glossary. |

\* Rubric items 5 and 6 have a "✓\*" because the single-PR format
inherently compresses what, in normal development, would be a series
of small commits. The rubric is a guide for recognising faithful
fixtures; single-PR exemplars satisfy its *intent* (honest Pragmatic
discipline with test-first sequencing) even when the git history is
one squash commit.

**10/10.**

---

## The findings on this exemplar

Running `gaudi check` against the Gaudí project with this exemplar
merged produces three kinds of findings, each meaningful:

### Category A — SMELL-003 LongFunction (×1)

`process_order` is ~80 lines. The rule says functions should be
shorter. This is a **universal** rule (`SMELL-003` was classified as
universal in the [rule audit](../../../../docs/rule-registry.md)),
and it fires correctly: a Pragmatic one-big-function is genuinely a
long function, and the rule is accurately reporting a real cost to
readability that the Pragmatic discipline accepts as a trade-off.

This finding should fire under *every* school's scope, including
`pragmatic`. The Pragmatic axiom does not say "long functions are
good"; it says "abstraction before duplication is more expensive
than the long function." Under the Rule of Three, once a second
pricing policy or a second validation rule shows up, this function
splits — and the SMELL-003 warning goes away as a natural consequence
of the split, not as a Gaudí scope decision.

### Category B — SMELL-004 LongParameterList (×1)

`process_order` takes 8 parameters. The rule says lists should be
shorter. Also **universal**, also correctly firing. Under Classical,
these parameters would have been constructor-injected into a
`ValidationService` + `PricingService` + `ReservationService`
composition root. The Pragmatic refusal of constructor injection is
the choice this finding makes visible.

Same outcome as SMELL-003: if a second caller needs the same state
plumbing, the Rule of Three fires and a small `_PipelineContext`
value object appears — and then SMELL-004 stops firing. Not before.

### Category C — STRUCT-021 MagicStrings (×4)

`"on_hand"`, `"reserved"`, `"sku"`, etc. appear multiple times because
the pipeline reads from plain dicts. A Classical exemplar would have
extracted these into `dataclass` field names and never repeated a
string literal. A Pragmatic exemplar deliberately prefers the plain
dict and accepts the STRUCT-021 findings as the honest cost of that
choice.

---

## Comparison with the Classical exemplar

| Property | Classical | Pragmatic |
|---|---|---|
| Files | 8 Python files across 4 layers | 1 Python file |
| Lines of code (impl) | ~450 | ~120 |
| Public classes | 12 | 0 |
| Protocols / interfaces | 5 | 0 |
| Single-method wrapper classes | 6 | 0 |
| `gaudi check` SMELL-014 | 6 findings (audit-predicted false positives under classical) | 0 findings |
| `gaudi check` SMELL-003 | 0 findings (services are short) | 1 finding (one big function) |
| `gaudi check` SMELL-004 | 0 findings | 1 finding |
| `gaudi check` STRUCT-021 | 2 findings | 4 findings |

**The same twelve tests pass against both implementations.** The
canonical task's seven invariants are enforced identically. What
differs is *where* the complexity lives: Classical pushes it into
explicit layers and protocols; Pragmatic keeps it inlined until
pressure forces a split.

Neither is wrong. They are the two faithful expressions of two
genuinely different axioms about when abstraction pays for itself.
Gaudí's [philosophy scope audit](../../../../docs/rule-registry.md)
is the editorial constitution that lets both exemplars score 10/10
against their own rubrics — the scoping system is what makes this
pluralism defensible instead of confused.

---

## Notes for future exemplars

When the Functional exemplar lands, the expected diff is: the pipeline
becomes a composition of pure functions, errors become tagged-union
return values, no mutation of passed-in dicts, and the in-memory state
is rebuilt from immutable values rather than mutated in place. The
twelve tests will pass.

When the Event-Sourced exemplar lands, `process_order` becomes a
command handler that emits `OrderPlaced`, `PricingCalculated`,
`InventoryReserved`, `OrderConfirmed` events, and the current state is
a projection rebuilt from the log. Again, the twelve tests pass.

Each of these contrasts is *what the schools disagree about*, and the
pair (Classical + Pragmatic) is now the anchor against which the other
six can be reviewed.

---

## See also

- [docs/philosophy/pragmatic.md](../../../../docs/philosophy/pragmatic.md) — The axiom sheet.
- [docs/philosophy/canonical-task.md](../../../../docs/philosophy/canonical-task.md) — The canonical task specification.
- [docs/rule-registry.md](../../../../docs/rule-registry.md) — The rule audit, including the scope tags that make the Classical and Pragmatic findings diverge as they should.
- [tests/philosophy/classical/canonical/README.md](../../classical/canonical/README.md) — The Classical reference exemplar; read this one's Category A findings alongside that one's to see what the scope system is doing.
