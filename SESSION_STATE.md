# Session State — Gaudi

## Last Updated
2026-04-11 (Phase 1 engine change landed)

## Current Status
Alpha (v0.1.1). Python-only architecture linter.
~124 implemented rules, with **philosophy-scope filtering active**:
22 rules tagged as scoped to specific schools, ~102 remain universal.

**Phase 1 is complete.** The engine respects `Rule.philosophy_scope`
and `[philosophy].school` in `gaudi.toml`. Phase 0 remaining (reference
exemplars for the other seven schools) is now the natural next step.

---

## What Changed This Session

Four PRs this session, all merged green without `--admin`:

1. **PR #160** — `feat(engine): Rule.philosophy_scope and [philosophy].school wiring`
   - `core.py`: `UNIVERSAL_SCOPE`, `VALID_SCHOOLS`, `VALID_SCOPE_TOKENS`,
     `DEFAULT_SCHOOL = "classical"`, and
     `Rule.philosophy_scope: frozenset[str] = UNIVERSAL_SCOPE`
     as a class attribute.
   - `config.py`: `[philosophy]` TOML table parsed, defaulted,
     validated. `get_school(config)` helper. `ValueError` on typo.
   - `pack.py`: `rule_applies_to_school(rule, school)` — the one
     predicate the base `Pack.check()` uses to filter rules.
   - Both Python and Ops packs plumb `school` through their `check()`
     and honor the filter.
   - 11 new unit tests (`tests/test_philosophy_scope.py`) including
     the guardrail that every registered rule's scope is a
     non-empty frozenset of known tokens.
   - **Behavior-preserving by design**: all rules default to
     `{"universal"}` via the class attribute.

2. **PR #161** — `feat(rules): tag 22 scoped rules per the philosophy audit`
   - Walked the Philosophy Scope Audit in
     [docs/rule-registry.md](docs/rule-registry.md) and attached
     `philosophy_scope` to every rule flagged as non-universal.
   - 22 rules tagged. Every tag carries an inline comment citing
     the axiom sheet that justifies the exclusion.
   - Updated `tests/test_fixture_corpus.py` so the per-rule fixture
     runner selects a school in which the rule under test actually
     runs — the fixture corpus is a per-rule specification and
     must run regardless of project-level scoping.
   - **End-to-end forcing-function validated**: under the default
     `classical` school, the six `SMELL-014` false positives on the
     Classical exemplar (documented in
     `tests/philosophy/classical/canonical/README.md`) disappeared
     entirely. `SMELL-018` also dropped to zero.

3. **PR #162** — `test(philosophy): cross-school matrix test for scope filtering`
   - New `tests/philosophy/test_philosophy_matrix.py` with 12 tests.
   - Classical reference exemplar exercised under **every one of
     the eight valid schools** with explicit required/forbidden
     rule sets.
   - Two load-bearing regression assertions:
     - `test_classical_exemplar_false_positives_resolved_under_classical`
       pins SMELL-014 as **not firing** under `classical`.
     - `test_classical_exemplar_under_pragmatic_does_fire_smell_014`
       pins SMELL-014 as **still firing** under `pragmatic`, proving
       the "same code, different verdict" property — the scope
       system filters per-school, it does not globally silence.
   - Two drift-catching guardrails:
     `test_every_school_in_matrix_is_valid` and
     `test_classical_exemplar_covered_by_every_school`.

4. **PR #163** — `chore(session): update SESSION_STATE for Phase 1 completion`
   - This file update.

Test suite: **529 passed** (was 506 at start of session; +23 new).

---

## The Load-Bearing Outcome

Before Phase 1, `gaudi check` running against
`tests/philosophy/classical/canonical/` produced six `SMELL-014
LazyElement` findings on the Repository implementations, Clock,
FixedClock, and ReservationIdGenerator — all documented in the
exemplar's README as audit-predicted false positives.

After Phase 1, under `school = "classical"` (the default), **those
six findings are gone**. Under `school = "pragmatic"`, they **come
back**. The engine is now doing exactly what the audit said it should.

```
rule       | baseline | classical | pragmatic
-----------|----------|-----------|----------
SMELL-014  |     7    |     0     |    7
SMELL-018  |     1    |     0     |    1
```

This is the "same code, different verdict" proof that the scope
system is doing something real, and it is pinned as a permanent
regression test.

---

## Phase Roadmap

**Phase 0 — scaffolding:**

- [x] 0a: Axiom sheets for eight schools (#155)
- [x] 0b: Rule audit with scope column (#156)
- [x] 0c: Canonical task statement (#157)
- [x] 0d: Classical reference exemplar (#158)

**Phase 0 remaining — reference exemplars (future PRs):**

- [ ] 0e: Pragmatic exemplar (the sharpest contrast with Classical)
- [ ] 0f: Functional exemplar
- [ ] 0g: Convention (Django) exemplar
- [ ] 0h: Resilience-First exemplar
- [ ] 0i: Unix exemplar
- [ ] 0j: Data-Oriented exemplar
- [ ] 0k: Event-Sourced exemplar

When each lands, a new set of rows is added to
`EXEMPLAR_EXPECTATIONS` in
`tests/philosophy/test_philosophy_matrix.py` and the matrix grows
automatically.

**Phase 1 — engine change (complete this session):**

- [x] `Rule.philosophy_scope` field (#160)
- [x] `[philosophy].school` in `gaudi.toml` (#160)
- [x] `rule_applies_to_school` one-predicate filter (#160)
- [x] Unit tests and guardrails (#160)
- [x] 22 scoped rules tagged per the audit (#161)
- [x] Fixture corpus runner adjusted to preserve per-rule specs (#161)
- [x] Cross-school matrix test for scope filtering (#162)

**Phase 2 — polish (future PRs, low priority):**

- [ ] CLI attribution in report output (show which philosophy
      a rule belongs to when it fires)
- [ ] `gaudi philosophy --explain` deterministic inference from
      project dependencies
- [ ] Detector precision issues found during Phase 0: SMELL-007
      over-fires on service classes, SMELL-023 confuses `Protocol`
      classes with real inheritance

---

## Things To Know Before Next Session

1. **The RFC file** `gaudi-architectural-philosophies.md` in the
   repo root is still untracked. Its content has been distilled
   into the eight axiom sheets plus the Phase 1 implementation.

2. **Default school is `classical`.** Any project that picks up
   this version of Gaudi without adding `[philosophy]` to its
   `gaudi.toml` will see the same rules fire as it did in v0.1.1,
   because Classical is the closest match to the implicit default
   that pre-Phase-1 Gaudi was using.

3. **Phase 2 polish is deferred.** The engine works end-to-end with
   zero UX additions. Attribution in report output and `gaudi init`
   wizards are nice-to-haves, not prerequisites for anything.

4. **The matrix test is the regression gate.** Any future change
   that breaks scope filtering — typo in a tag, accidental
   un-scoping, drift between the audit and the code — should fail
   `tests/philosophy/test_philosophy_matrix.py` loudly.

5. **Next natural piece of work: Pragmatic exemplar.** It is the
   sharpest philosophical contrast with Classical on the same
   canonical task, and writing it will immediately exercise the
   matrix's pragmatic row beyond the Classical exemplar's
   negative check.

---

## Test Suite / Build Status

- `ruff check .` — clean
- `ruff format --check .` — 532 files formatted
- `pytest --tb=short -q` — **529 passed**, 3 warnings
- `gaudi check` on the Gaudí project itself — six SMELL-014 and
  one SMELL-018 findings removed relative to pre-Phase-1 baseline
- CI: every PR this session merged green without `--admin`

---

## Commits Landed (this session, in order)

```
63ca682 test(philosophy): add cross-school matrix test for scope filtering (#162)
2129031 feat(rules): tag 22 scoped rules per the philosophy audit (#161)
bdc0af6 feat(engine): Rule.philosophy_scope and [philosophy].school wiring (#160)
9289def chore(session): update SESSION_STATE with overnight multi-philosophy work (#159)
```

Branch tip: `main`. No open PRs from this session once #163 lands.
No uncommitted changes other than the untracked RFC file.
