# Session State — Gaudi

## Last Updated
2026-04-11 (end of Phase 0g session — 5 of 8 reference exemplars landed)

## Current Status
Alpha (v0.1.1). Python-only architecture linter.
~124 implemented rules, 23 scoped to specific schools, ~101 universal.
**Phase 1 engine complete.** Rule.philosophy_scope + [philosophy].school
in gaudi.toml filter rules per school.
**Phase 0 exemplars: 5 of 8 complete.** Classical, Pragmatic,
Functional, Unix, Convention all on main. Resilient, Data-Oriented,
Event-Sourced remaining.

Test suite: **625 passed**, 3 warnings. Ruff clean.

---

## What Changed This Session

This session picked up from Phase 1 completion and shipped five
reference exemplars plus one audit revision. Ten PRs merged, all
green via CI, none bypassed.

### Reference exemplars shipped

| PR | Exemplar | Files | Distinctive shape |
|---|---|---|---|
| #158 (prior session) | Classical | 8 across 4 layers | OOP tree with Repository Protocol |
| #164 | Pragmatic | 1 | Single straight-through function, honest duplication |
| #165 | Functional | 3 | Pure transformations, frozen records, Ok/Err return |
| #166 | Unix | 4 | Independent programs, JSON-lines on stdio, real subprocess pipeline test |
| **#167** | **Convention (Django)** | 8 Django files | Manager method composition root, admin + migrations |

Each exemplar passes the same 12 acceptance tests against the same
shared seed data at [tests/philosophy/seed_data.py](tests/philosophy/seed_data.py).
What differs is where the complexity lives.

### Audit revisions driven by the exemplars

The exemplar workflow is designed to be a forcing function: writing
a faithful implementation of a school surfaces rules that fire
incorrectly, and the evidence justifies scope revisions. This
session produced two audit revisions:

1. **#166 (Unix)** moved `ARCH-013 FatScript` from universal to
   scoped-away-from-`unix`. Evidence: the Unix stages tripped it on
   `main()` functions that were pure argparse + stdin loop + atomic
   write plumbing. Under Unix catechism #1, the script IS the
   service — there is no "service elsewhere" to extract to.

2. **#167 (Convention)** did NOT add new scope tags but surfaced
   **six detector precision issues** (the richest single-exemplar
   yield so far), documented in
   [tests/philosophy/convention/canonical/README.md](tests/philosophy/convention/canonical/README.md)
   as follow-up work for a fresh session. Listed below under
   "Things To Know."

### The matrix now pins three independent same-code-different-verdict demonstrations

Before this session the matrix had one: the Classical exemplar
tripped `SMELL-014 LazyElement` under pragmatic/unix/functional/
data-oriented but stayed silent under classical. This session added
two more:

| Exemplar | Rule | Fires under | Silent under |
|---|---|---|---|
| Classical | `SMELL-014` | pragmatic, unix, functional, data-oriented | **classical**, convention, resilient, event-sourced |
| Unix | `ARCH-013` | everywhere except unix | **unix** |
| Convention | `SMELL-014` | pragmatic, unix, functional, data-oriented | **convention**, classical, resilient, event-sourced |

The Classical and Convention demonstrations are symmetric — both are
"clean at home, dirty abroad" for the same rule on different kinds
of framework seams (Repository Protocols vs Django Managers).

Two exemplars are **scope-invariant** control conditions (Pragmatic
and Functional): their finding sets are bit-identical under every
valid school, pinning the property that universal rules must not
shift. `test_scope_invariant_exemplar_is_stable_across_schools`
parametrizes over both.

### Test matrix size

- Classical acceptance: 12 tests
- Pragmatic acceptance: 12 tests
- Functional acceptance: 14 tests (+ 4 rubric-enforcing)
- Unix acceptance: 15 tests (including real subprocess pipeline + 2 AST rubric tests)
- Convention acceptance: 14 tests (+ admin-registration and migration-drift tests)
- Matrix rows: 40 parametrized + 11 dedicated regression assertions

Total philosophy suite: **120 tests**. Total project suite: **625**.

---

## Dependencies Added

**`django>=5.0,<6.0; python_version<'3.14'`** in
`[project.optional-dependencies].dev`.

- **Test-only.** Never installed for end users via `pip install gaudi-linter`.
- Pinned to 5.x LTS for CI predictability across Python 3.10-3.13.
- Python 3.14 guard: `pytest.importorskip('django')` in the
  Convention test module skips cleanly when Django isn't installed.
- Gaudi has **zero runtime dependency** on Django. Every `DJ-*`,
  `DRF-*`, and Django-aware rule lints user projects via AST
  inspection, not by importing their code. The dep is exclusively
  for writing the Convention reference exemplar.

---

## Phase Roadmap

### Phase 0 — reference exemplars (5/8 complete)

- [x] **0a-0d**: Axiom sheets, rule audit, canonical task statement, Classical exemplar (prior session)
- [x] **0e**: Pragmatic exemplar (#164)
- [x] **0f**: Functional exemplar (#165)
- [x] **0i**: Unix exemplar (#166) — reordered ahead of 0g
- [x] **0g**: Convention (Django) exemplar (#167)
- [ ] **0h**: Resilience-First exemplar — stdlib-only, should surface `STAB-*` forcing-function evidence
- [ ] **0j**: Data-Oriented exemplar — may want numpy as optional dep, symmetric to the Django dep decision
- [ ] **0k**: Event-Sourced exemplar — stdlib-only, most conceptually complex

### Phase 1 — engine change (complete in prior session, PRs #160-162)

### Phase 2 — detector precision fixes (new, forced by this session)

The Convention exemplar surfaced six detector precision issues. All
are documented in
[tests/philosophy/convention/canonical/README.md](tests/philosophy/convention/canonical/README.md)
Category B with specific fix recommendations:

1. **DOM-001 AnemicDomainModel** doesn't recognize Django Managers
   as business-logic carriers. A model with an
   `objects = CustomerManager()` assignment and a Manager subclass
   with domain-named query methods should not count as anemic.
2. **SCHEMA-001 MissingTimestamps** should be aware of
   reference-vs-transactional shape. Reference data (`Product`,
   `PromoCode`) doesn't need audit columns; only mutable tables do.
3. **SEC-001 NoMetaPermissions** fires on every Django model despite
   Django auto-creating add/change/delete/view permissions. Should
   only fire on models without the four auto-generated permissions
   OR on models in security-sensitive locations.
4. **STAB-001 UnboundedResultSet** fires on `.filter(...).first()`.
   `.first()` is the opposite of unbounded. Should walk the full
   attribute chain and skip filter chains that terminate in
   `.first()`, `.get()`, or `[offset:]`.
5. **DJ-SEC-001 DjangoSecretKeyExposed** fires on labeled test
   settings. Should skip `settings.py` files under `test/` /
   `tests/` / `conftest.py`, OR respect `# noqa: DJ-SEC-001`, OR
   detect obvious test placeholders ("test" / "example" / "dummy").
6. **SEC-003 NoDefaultManager** fires despite `objects = CustomerManager()`
   — the custom manager assignment satisfies the "default manager
   exists" requirement but the detector doesn't see it.

Also noted in earlier exemplar READMEs (prior session):

- **SMELL-007 DivergentChange** over-fires on Classical service
  classes with multiple methods serving one responsibility.
- **SMELL-023 RefusedBequest** confuses `Protocol` classes with
  real inheritance.
- **SMELL-008 ShotgunSurgery** fires on Functional `ResolvedLines`
  type alias (addressed by inlining, not by fixing the detector).

Total: **9 detector precision issues** documented as follow-up.

### Phase 3 — polish (deferred)

- CLI attribution in report output (show which philosophy a rule
  belongs to when it fires)
- `gaudi philosophy --explain` deterministic inference from project
  dependencies
- Website audit: run `gaudi check` against Nathan's real Django
  website, categorize findings, surface audit gaps driven by
  production evidence (not an exemplar fixture)

---

## Things To Know Before Next Session

1. **PRs merged this session (10 total)** — all on main:
   - #160 engine wiring (Phase 1A)
   - #161 scope tags (Phase 1B)
   - #162 matrix test (Phase 1C)
   - #163 SESSION_STATE for Phase 1
   - #164 Pragmatic exemplar (Phase 0e)
   - #165 Functional exemplar (Phase 0f)
   - #166 Unix exemplar + ARCH-013 scope revision (Phase 0i)
   - #167 Convention exemplar (Phase 0g)
   - Plus this SESSION_STATE update

2. **The RFC file** `gaudi-architectural-philosophies.md` in the
   repo root is still untracked. It has been fully distilled into
   the axiom sheets, the rule audit, the Phase 1 implementation,
   and the five exemplars.

3. **Django is installed in both conda envs** I used:
   - `Oversteward` (the primary conda env per project config)
   - `ai-assistants` (the env pytest actually uses — this was
     discovered during the Functional exemplar debugging; pytest
     was finding tests via src/ layout but importing Python from
     a different env)

4. **CI install time impact**: adding Django added ~3 seconds to
   the install step, unchanged test runtime. No pip-audit hits.

5. **My session-weight recommendation** was to stop here and start
   fresh for the remaining three exemplars and the detector
   precision fixes. This session's context carries every axiom
   sheet, every exemplar, every probe output, and the full Phase 1
   engine implementation. A fresh session will read SESSION_STATE,
   read the Convention README for the detector issue list, and
   work from that without the session-history overhead.

6. **The highest-value next session** would be one of:
   - **Option A: Resilience-First exemplar.** Stdlib-only,
     well-scoped, one PR. Good if you want to continue the Phase 0
     exemplar series linearly.
   - **Option B: Detector precision fixes (batch of 3-4).** The
     Convention README has six with specific fix recommendations;
     a single PR could address the top three (DOM-001 Manager
     awareness, STAB-001 `.first()` handling, DJ-SEC-001 test-file
     skip). Good if you want to tighten the audit before the
     remaining exemplars.
   - **Option C: Website audit.** Run `gaudi check` against Nathan's
     real Django website, categorize findings, triage with Nathan
     in the loop. Highest leverage but needs Nathan present.

7. **Gotchas that bit me this session:**
   - Conda run on Windows rejects newline characters in `python -c`
     arguments; I wrote throwaway `scripts/_probe_*.py` files
     instead and deleted them before committing.
   - The Classical `@property` on `InventoryLevel`/`PromoCode` was
     originally a single-method class under the Functional exemplar's
     strict reading and tripped SMELL-014 under functional. I
     refactored the dataclasses to have zero methods and moved
     helpers to free functions in `pipeline.py`. This is a lesson
     about how strict the Functional axiom actually is.
   - Writing PR B (scope tags) from a branch that was pre-PR-A
     (engine wiring) meant the tags had no runtime effect until I
     rebased after PR A merged. The tags compose correctly across
     commits but the tests for scope-awareness only fire once the
     engine change lands.

8. **The Convention exemplar is the richest detector fuzzer** for
   the Django-aware rule family. Running `gaudi check` against any
   real Django project will surface the same six precision issues
   — but the exemplar is a clean, isolated, tested, reviewable
   reference case for each of them.

---

## Test Suite / Build Status

- `ruff check .` — clean
- `ruff format --check .` — 559 files formatted
- `pytest --tb=short -q` — **625 passed**, 3 warnings
- `pytest tests/philosophy/ -q` — 120 passed (5 exemplars × ~20-24 tests each + 51 matrix rows/assertions)
- `gaudi check` on the Gaudí project itself — stable baseline,
  findings on the exemplars match matrix expectations per school
- CI: every PR this session merged green without `--admin`

---

## Commits Landed (this session, in order)

```
50bafeb test(philosophy): add Convention (Django) reference exemplar + matrix rows (#167)
57d87a2 test(philosophy): add Unix reference exemplar + scope ARCH-013 away from unix (#166)
72eefcf test(philosophy): add Functional reference exemplar + matrix rows (#165)
f2711e8 test(philosophy): add Pragmatic reference exemplar + matrix rows (#164)
9289def chore(session): update SESSION_STATE with overnight multi-philosophy work (#159)
0795447 chore(session): update SESSION_STATE for Phase 1 completion (#163)
63ca682 test(philosophy): add cross-school matrix test for scope filtering (#162)
2129031 feat(rules): tag 22 scoped rules per the philosophy audit (#161)
bdc0af6 feat(engine): Rule.philosophy_scope and [philosophy].school wiring (#160)
```

Branch tip: `main`. No open PRs after this SESSION_STATE update
lands. No uncommitted changes other than the untracked RFC file.
