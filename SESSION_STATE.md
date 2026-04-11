# Session State — Gaudi

## Last Updated
2026-04-11 (end of Phase 0jk session — Phase 0 reference exemplars 8/8 complete)

## Current Status
Alpha (v0.1.1). Python-only architecture linter.
~124 implemented rules, 23 scoped to specific schools, ~101 universal.
**Phase 1 engine complete.** Rule.philosophy_scope + [philosophy].school
in gaudi.toml filter rules per school.
**Phase 0 exemplars: 8 of 8 COMPLETE.** Classical, Pragmatic, Functional,
Unix, Convention, Resilient, Data-Oriented, Event-Sourced. Every school
in the philosophy matrix now has a faithful reference exemplar.

Test suite: **711 passed**, 3 warnings. Ruff clean.

---

## What Changed This Session

This session picked up from Phase 0h (Resilient exemplar already merged
on main at session start) and shipped the final two reference
exemplars, closing out Phase 0.

### Reference exemplars shipped

| PR | Exemplar | Files | Distinctive shape |
|---|---|---|---|
| #170 | **Data-Oriented** | 3 impl + 1 bench | SoA numpy columns (int64 cents, uint8 standing), batch pipeline stage-by-stage, np.add.at scatter-reduce, frozen-slots World, measured benchmark at N ∈ {1..10k} |
| #171 | **Event-Sourced** | 6 files | 11 frozen event types (incl. 6 intent-carrying rejections), in-process append-only store, pure aggregate command handler, 2 projections with rebuild, time-travel query |

Both shipped with full rubric READMEs and 10/10 rubric scores against
their respective axiom sheets. Both merged via CI without `--admin`.

### The matrix has reached its intended shape

With all eight exemplars landed, the matrix now pins:

**Three same-code-different-verdict demonstrations** (the scoped-rule
proofs):
- Classical SMELL-014 (clean under classical, dirty under pragmatic/
  unix/functional/data-oriented)
- Unix ARCH-013 (clean under unix, dirty under every other school)
- Convention SMELL-014 (clean under convention/classical, dirty under
  pragmatic/unix/functional/data-oriented)

**Four scope-invariant control conditions** (the universal-rule proofs):
- Pragmatic — single function, no classes
- Functional — frozen records, Ok/Err
- Resilient — timeouts + retries + breaker, stdlib only
- **Event-Sourced** — frozen events + replay + time-travel (this session)

Data-Oriented is *nearly* scope-invariant (LOG-004 on print() in bench.py
is scoped away from unix, producing a 4-rule delta between the unix row
and every other school's row). Not a Data-Oriented axiom claim, so the
exemplar does not join SCOPE_INVARIANT_EXEMPLARS; its matrix rows pin
required/forbidden sets directly.

### Audit revisions surfaced this session

**None.** Both exemplars trip only universal-cost rules. No new
forcing-function revisions were justified by the Data-Oriented or
Event-Sourced evidence.

The Convention exemplar (prior session) remains the richest detector-
fuzzer for the Django-aware rule family, with six documented precision
issues in `tests/philosophy/convention/canonical/README.md` still
awaiting fix PRs.

### Test matrix size

- Classical acceptance: 12 tests
- Pragmatic acceptance: 12 tests
- Functional acceptance: 14 tests (+ 4 rubric-enforcing)
- Unix acceptance: 15 tests (+ subprocess pipeline + AST rubric)
- Convention acceptance: 14 tests (+ admin + migration-drift)
- Resilient acceptance: 20 tests (incl. retry/breaker/idempotency)
- **Data-Oriented acceptance: 18 tests** (incl. 6 SoA rubric tests,
  1 np.add.at scatter test, dtype pinning)
- **Event-Sourced acceptance: 19 tests** (incl. frozen events,
  aggregate purity, projection rebuild matches live, time-travel
  with negative history, new-projection-without-writes, intent-
  carrying names, OrderPlaced-always-first)
- Matrix rows: ~72 parametrized expectations + 14 dedicated regression
  assertions (scope-invariance, same-code-different-verdict pairs,
  one-per-exemplar-covers-every-school drift catchers)

Total philosophy suite: **206 tests**. Total project suite: **711**.

---

## Dependencies Added

**`numpy>=1.26`** added to `[project.optional-dependencies].dev`
this session (PR #170), symmetric to the Django decision from the
Convention exemplar in the prior session.

- **Test-only.** Never installed for end users via `pip install gaudi-linter`.
- Gaudi has **zero runtime dependency** on numpy. Every rule lints
  user projects via AST inspection, never by executing their code.
- The Data-Oriented test module uses `pytest.importorskip("numpy")`
  so CI on any environment where numpy cannot be installed still
  stays green; in practice numpy installs cleanly on every Python
  3.10–3.14 wheel we target.

Both optional dev deps now live side by side:

```toml
"django>=5.0,<6.0; python_version<'3.14'",
"numpy>=1.26",
```

---

## Phase Roadmap

### Phase 0 — reference exemplars (8/8 COMPLETE)

- [x] **0a-0d**: Axiom sheets, rule audit, canonical task, Classical
- [x] **0e**: Pragmatic (#164)
- [x] **0f**: Functional (#165)
- [x] **0i**: Unix + ARCH-013 scope revision (#166)
- [x] **0g**: Convention/Django (#167)
- [x] **0h**: Resilience-First (#169)
- [x] **0j**: Data-Oriented (#170, this session)
- [x] **0k**: Event-Sourced (#171, this session)

### Phase 1 — engine change (complete)

### Phase 2 — detector precision fixes (still pending)

The Convention exemplar (prior session) surfaced six documented
detector precision issues in `tests/philosophy/convention/canonical/README.md`
Category B:

1. DOM-001 AnemicDomainModel — not aware of Django Managers as
   business-logic carriers.
2. SCHEMA-001 MissingTimestamps — fires on reference data; should
   distinguish reference-vs-transactional.
3. SEC-001 NoMetaPermissions — fires on every Django model despite
   auto-created add/change/delete/view permissions.
4. STAB-001 UnboundedResultSet — fires on `.filter(...).first()`.
5. DJ-SEC-001 DjangoSecretKeyExposed — fires on labeled test settings.
6. SEC-003 NoDefaultManager — not seeing `objects = CustomerManager()`.

Plus from earlier exemplars:

- SMELL-007 DivergentChange over-fires on Classical service classes.
- SMELL-023 RefusedBequest confuses Protocol classes with real
  inheritance.
- SMELL-008 ShotgunSurgery fired on Functional ResolvedLines type
  alias (addressed by inlining, not by detector fix).

**Total: 9 detector precision issues documented as follow-up work.**
These are the highest-value next PRs — every one of them has a
specific fix recommendation, a reference exemplar that will
regression-test the fix, and a concrete test of "same code, cleaner
finding set" to pin the before/after.

### Phase 3 — polish (deferred)

- CLI attribution in report output (show which philosophy a rule
  belongs to when it fires)
- `gaudi philosophy --explain` deterministic inference from project
  dependencies
- Website audit: run `gaudi check` against Nathan's real Django
  website, categorize findings, surface audit gaps driven by
  production evidence

---

## Things To Know Before Next Session

1. **PRs merged this session (2 total)** — both on main:
   - #170 Data-Oriented exemplar + matrix rows + numpy dev dep
   - #171 Event-Sourced exemplar + matrix rows

2. **The RFC file** `gaudi-architectural-philosophies.md` in the
   repo root is still untracked. It has been fully distilled into
   the axiom sheets, the rule audit, the Phase 1 implementation,
   and now all eight exemplars. Safe to delete or move to docs/.

3. **Python environment note** (carryover from prior session): the
   `Oversteward` conda env is the canonical dev env per project
   config, but pytest in this codebase actually runs via the
   `ai-assistants` conda env because of the src/ layout and sys.path
   interaction. Both envs have the dev dependencies installed. Any
   `conda run -n Oversteward pytest` command works; so does running
   pytest directly from `ai-assistants`. Standalone python scripts
   that `import gaudi` must set `PYTHONPATH=src` to get the dev
   source instead of the installed wheel.

4. **Windows conda gotcha** (still true): `conda run -n Oversteward
   python -c` rejects newlines in the argument. For multi-line
   Python, write a script under `scripts/_probe_*.py` and delete it
   before committing. Every probe script this session was built and
   deleted that way.

5. **Reservation id shape** — the Event-Sourced exemplar derives
   reservation ids deterministically from order_id + first sku
   (`RES-<6char>`) rather than a monotonic counter, so replay
   produces the same ids as the original run. The other exemplars
   use a counter (`RES-000001`, `RES-000002`). Both shapes satisfy
   the acceptance tests' `startswith('RES-')` check.

6. **The Data-Oriented benchmark** (`tests/philosophy/data_oriented/
   canonical/bench.py`) has measured numbers in its docstring for
   N ∈ {1..10k}. Rerun the script if you change the pipeline and
   update the docstring if the per-order cost drifts materially
   (say, >30%). The benchmark does not claim "numpy beats Python";
   it reports the actual per-order cost as a function of batch
   size and names the degenerate zone (N < ~100).

7. **The highest-value next session** is one of:
   - **Option A: Detector precision fixes.** Nine documented issues
     with specific fix recommendations. Ship in batches of 2–4 per
     PR. Highest leverage because every exemplar can regression-
     test the fix. Recommended ordering: start with DOM-001 Manager
     awareness and STAB-001 `.first()` handling (both Convention-
     surfaced) because the Convention exemplar is the richest
     fuzzer and Django is the most widely-linted framework.
   - **Option B: Phase 3 polish** — CLI attribution, philosophy
     `--explain`, website audit.
   - **Option C: Clean up the RFC file** — delete or move
     `gaudi-architectural-philosophies.md` to `docs/` now that its
     content is fully distributed across axiom sheets and exemplars.

8. **Gotchas that bit me this session:**
   - First cut of the Data-Oriented benchmark claimed "2.3x faster
     than naive baseline" against a baseline that was deliberately
     too minimal. The numbers were false, not in direction but in
     magnitude, and the comparison wasn't meaningful because the
     two code paths did different amounts of work. Rewrote to scan
     batch sizes instead and report the honest per-N costs; no
     baseline comparison. Lesson: any benchmark that compares
     against a "naive baseline" must verify the baseline does
     equivalent work, or the comparison is noise pretending to be
     signal. When in doubt, report absolute numbers and let the
     reader decide.
   - `conda run -n Oversteward python -c` with newlines produced
     the Windows conda crash report again. Every probe in this
     session went through a throwaway `scripts/_probe_*.py` file
     and was deleted before commit (same workflow as prior sessions).
   - numpy wasn't installed in Oversteward on session start; had to
     `pip install numpy` directly via the env's Python. ai-assistants
     already had numpy 2.4.1. Both envs now have numpy.

---

## Test Suite / Build Status

- `ruff check .` — clean
- `ruff format --check .` — clean
- `pytest --tb=short -q` — **711 passed**, 3 warnings
- `pytest tests/philosophy/ -q` — **206 passed** (8 exemplars × 12–20
  acceptance tests each + 72 parametrized matrix rows + 14 dedicated
  regression assertions)
- `gaudi check` on the Gaudí project itself — 1 pre-existing error
  (DJ-SEC-001 on `tests/philosophy/convention/canonical/settings.py:15`,
  the labeled test settings module; documented as detector issue #5)
- CI: every PR this session merged green without `--admin`

---

## Commits Landed (this session, in order)

```
510e8e7 test(philosophy): add Event-Sourced reference exemplar + matrix rows (#171)
80179a8 test(philosophy): add Data-Oriented reference exemplar + matrix rows (#170)
```

Branch tip: `main`. No open PRs after this SESSION_STATE update
lands. No uncommitted changes other than the untracked RFC file.
