# Session State — Gaudi

## Last Updated
2026-04-11 (overnight session)

## Current Status
Alpha (v0.1.1). Python-only architecture linter.
~124 implemented rules, ~82% universal / ~18% scoped-to-a-philosophy
(per the new rule audit).

Multi-philosophy work Phase 0 is **complete**. Phase 1 (engine wiring
for `Rule.philosophy_scope`) is the next logical step and has concrete
forcing-function evidence ready to drive it.

---

## What Changed This Session (Overnight)

Four PRs planned, all merged. In order:

1. **PR #155** — `docs(philosophy): axiom sheets for eight architectural schools`
   - New directory `docs/philosophy/` with eight axiom sheets + a README index.
   - Schools: Classical, Pragmatic, Functional, Unix, Resilience-First,
     Data-Oriented, Convention, **Event-Sourced** (added after review
     because it generates rules that contradict other schools, not
     merely stack).
   - Strict eight-section format per sheet: prime axiom, rejected
     alternative, canonical citations, catechism, rule shape,
     degenerate case, exemplar temptation, ten-item rubric.

2. **PR #156** — `docs(registry): philosophy scope audit for all implemented rules`
   - New "Philosophy Scope Audit" section in `docs/rule-registry.md`.
   - Tagged every implemented rule as either `universal` or scoped
     to specific schools, with one-sentence justifications that
     appeal to the relevant axiom sheet.
   - **Result: ~102 of ~124 rules (82%) universal; ~22 (18%) scoped.**
     This validates the hypothesis that the engine change needed to
     support multi-philosophy scoping is small rather than sprawling.
   - Two schools do most of the scoping work: **Convention**
     (blesses patterns other schools smell — fat models, single-file
     models) and **Data-Oriented** (refuses abstractions other
     schools assume — pipelines, wrapped primitives).

3. **PR #157** — `docs(philosophy): canonical task statement`
   - New `docs/philosophy/canonical-task.md`.
   - Defines the domain problem every school's reference
     implementation will solve: order processing pipeline
     (validation, pricing, inventory reservation, notification).
   - Seven enforceable invariants, shared domain (Customer, Product,
     Inventory, PromoCode, Order), acceptance criteria, out-of-scope
     exclusions, scoring procedure, and the planned implementation
     order (Classical → Pragmatic → Functional → Convention →
     Resilience-First → Unix → Data-Oriented → Event-Sourced).

4. **PR #158** — `test(philosophy): Classical reference exemplar`
   - New `tests/philosophy/` package.
   - `seed_data.py` with 10 test-case orders covering every
     acceptance criterion.
   - `classical/canonical/` directory: full three-layer Classical
     implementation of the order pipeline (domain/,
     infrastructure/, services/, pipeline.py).
   - `classical/test_canonical.py`: 12 new end-to-end tests.
   - `classical/canonical/README.md`: rubric-by-rubric score (10/10)
     with evidence column, plus categorized analysis of the
     remaining `gaudi check` findings.
   - Total project test suite: **494 → 506 passing** (+12 new).
   - Added `tests/philosophy/seed_data.py` to `gaudi.toml` excludes.

---

## The Load-Bearing Result

Running `gaudi check` against the new Classical exemplar produces
**six `SMELL-014 LazyElement` findings** on Repository implementations,
Clock, FixedClock, and ReservationIdGenerator.

The audit in `docs/rule-registry.md` already tags `SMELL-014` as scoped
to `{pragmatic, unix, functional, data-oriented}` — **explicitly not
Classical**. These six findings are exactly what the audit predicted
would be false positives on a faithful Classical exemplar.

**This is the single clearest forcing-function evidence that Phase 1
(the `Rule.philosophy_scope` engine change) is needed.** When the
engine respects philosophy scope, these false positives disappear on
this exemplar while continuing to fire correctly on Pragmatic/Unix
exemplars where single-method wrapper classes would indicate real
overengineering.

---

## Artifacts Created

```
docs/philosophy/
├── README.md                # index, rationale, contribution rules
├── canonical-task.md        # the order-processing problem statement
├── classical.md             # the default
├── pragmatic.md
├── functional.md
├── unix.md
├── resilient.md
├── data-oriented.md
├── convention.md
└── event-sourced.md

docs/rule-registry.md
└── (new section) Philosophy Scope Audit

tests/philosophy/
├── seed_data.py             # shared across all schools
└── classical/
    ├── canonical/
    │   ├── README.md        # rubric 10/10 + finding classification
    │   ├── domain/models.py
    │   ├── infrastructure/clock.py
    │   ├── infrastructure/repositories.py
    │   ├── services/validation.py
    │   ├── services/pricing.py
    │   ├── services/reservation.py
    │   ├── services/notification.py
    │   └── pipeline.py
    └── test_canonical.py

gaudi.toml                   # + tests/philosophy/seed_data.py exclude
```

Untracked (deliberately not committed — Nathan's working RFC):
- `gaudi-architectural-philosophies.md`

---

## Phase Roadmap

**Phase 0 — scaffolding (complete overnight):**

- [x] 0a: Axiom sheets for eight schools (PR #155)
- [x] 0b: Rule audit with scope column (PR #156)
- [x] 0c: Canonical task statement (PR #157)
- [x] 0d: Classical reference exemplar (PR #158)

**Phase 0 remaining — more reference exemplars (follow-up PRs):**

- [ ] 0e: Pragmatic exemplar (the sharpest contrast with Classical)
- [ ] 0f: Functional exemplar
- [ ] 0g: Convention (Django) exemplar
- [ ] 0h: Resilience-First exemplar
- [ ] 0i: Unix exemplar
- [ ] 0j: Data-Oriented exemplar
- [ ] 0k: Event-Sourced exemplar

**Phase 1 — engine change (deferred until Nathan approves):**

- [ ] Add `Rule.philosophy_scope: frozenset[str] = frozenset({"universal"})`
- [ ] Add `[philosophy].school` key to `gaudi.toml`
- [ ] One-predicate filter in `engine.py`: a rule runs iff
      `"universal" in rule.philosophy_scope or school in rule.philosophy_scope`
- [ ] Tag the ~22 scoped rules per the audit's findings
- [ ] Verify the six audit-predicted false positives on the Classical
      exemplar disappear when `school = "classical"`

**Phase 2 — matrix test (after Phase 1):**

- [ ] `tests/philosophy/test_philosophy_matrix.py` — parametrized over
      (school, exemplar) pairs; asserts expected-finding deltas.

**Phase 3 — philosophy inference (after Phase 2):**

- [ ] `gaudi philosophy --explain` deterministic inference from
      project dependencies (Django → convention, heavy immutability
      → functional, etc.).

---

## Things To Know Before Next Session

1. **The RFC file in the repo root** (`gaudi-architectural-philosophies.md`)
   is Nathan's working document. Do not commit it. It has already served
   its purpose — its content has been distilled into the eight axiom
   sheets under `docs/philosophy/`.

2. **`gaudi check` running on the classical exemplar produces the
   expected false positives.** This is not a regression — it is the
   forcing-function evidence for Phase 1. The README inside the
   exemplar directory categorizes every finding.

3. **SMELL-007 and SMELL-023 detector precision issues** were observed
   but not fixed. SMELL-007 (DivergentChange) over-fires on service
   classes with multiple methods serving one responsibility. SMELL-023
   (RefusedBequest) confuses Protocol classes with real inheritance.
   Both are good follow-up issues; the audit's engine-change does not
   resolve them.

4. **The seed data is intentionally shared and immutable.** Every
   school's implementation must run against `tests/philosophy/seed_data.py`
   unchanged so that differences in output are attributable to
   architectural differences, not test setup.

5. **Next exemplar: Pragmatic.** It should be a straight-through
   function with tests around it, no Repository Protocol, no services
   extracted until the Rule of Three fires. The diff against Classical
   is exactly what teaches the philosophical difference.

---

## Test Suite / Build Status

- `ruff check .` — clean
- `ruff format --check .` — 530 files formatted
- `pytest --tb=short -q` — **506 passed**, 3 warnings
- `gaudi check` — baseline project findings plus the documented
  philosophy exemplar findings (all categorized in the exemplar README)
- CI: every PR this session merged green without `--admin`

---

## Commits Landed (this session, in order)

```
aee2750 test(philosophy): add Classical reference exemplar of canonical task (#158)
bc582de docs(philosophy): add canonical task statement for reference exemplars (#157)
85e8c1f docs(registry): add philosophy scope audit for all implemented rules (#156)
9a01656 docs(philosophy): add axiom sheets for eight architectural schools (#155)
```

Branch tip: `main`. No open PRs from this session. No uncommitted
changes other than the untracked RFC file.
