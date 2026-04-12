# Session State — Gaudi

## Last Updated
2026-04-11 (Phase 2 detector precision fixes — 8 of 9 issues resolved)

## Current Status
Alpha (v0.1.1). Python-only architecture linter.
~124 implemented rules, 23 scoped to specific schools, ~101 universal.
**Phase 1 engine complete.** Rule.philosophy_scope + [philosophy].school
in gaudi.toml filter rules per school.
**Phase 0 exemplars: 8 of 8 COMPLETE.**
**Phase 2 detector precision: 8 of 9 issues resolved.** Only SMELL-008
ShotgunSurgery on Functional type alias remains (addressed by inlining
in the exemplar, not by detector fix — no PR needed).

Test suite: **722 passed**. Ruff clean.

---

## What Changed This Session

This session shipped Phase 2 — the detector precision fixes documented
in the Convention and Classical exemplar READMEs. Four PRs merged,
resolving 8 of the 9 documented false positives.

### PRs merged this session (4 total)

| PR | Rules fixed | Key change |
|---|---|---|
| #173 | DOM-001, STAB-001 | Manager awareness for DOM-001; chain-terminal methods (.first(), .get()) for STAB-001 |
| #174 | DOM-001, DJ-SEC-001, SEC-003 | Generic Manager types (Manager["Model"]); test-placeholder SECRET_KEY skip; test-prefixed credential value skip |
| #175 | SCHEMA-001, SEC-001 | Reference-data model exemption (no FK + no mutable-state fields); security-sensitive models only for permissions check |
| #176 | SMELL-007, SMELL-023 | Init-injected dependency exemption for disjoint analysis; Protocol added to ignored bases |

### Detector precision issue resolution matrix

| # | Rule | Issue | Resolution | PR |
|---|---|---|---|---|
| 1 | DOM-001 | Not aware of Django Managers | Manager method counting + generic type support | #173, #174 |
| 2 | SCHEMA-001 | Fires on reference data | Skip models with no FK and no mutable-state fields | #175 |
| 3 | SEC-001 | Fires on every Django model | Only fire on security-sensitive model names/paths | #175 |
| 4 | STAB-001 | Fires on .filter().first() | Walk chain for terminal methods (.first(), .get()) | #173 |
| 5 | DJ-SEC-001 | Fires on test settings | Skip test-placeholder SECRET_KEY values | #174 |
| 6 | SEC-003 | Not in original list | SEC-003 double-fires on test SECRET_KEY; test-prefix detection added | #174 |
| 7 | SMELL-007 | Over-fires on service classes | Exclude init-injected dependency attrs from disjoint analysis | #176 |
| 8 | SMELL-023 | Confuses Protocol classes | Add Protocol to _IGNORED_BASES | #176 |
| 9 | SMELL-008 | Functional type alias | Addressed by inlining in exemplar, not detector fix | N/A |

### Convention exemplar findings after Phase 2

Before Phase 2: 2 errors, 17 warnings, 20 infos (39 total).
After Phase 2: 0 errors, 12 warnings, 13 infos (25 total).
Delta: -14 findings eliminated (all false positives).

Remaining findings are correct: DOM-001 on Notification (genuinely
anemic, no Manager), SCHEMA-001 on OrderLine (has FKs, no timestamps),
SMELL-003 on place_order (100-line composition root), plus universal
STRUCT/IDX/OPS findings the exemplar intentionally doesn't address.

### Classical exemplar findings after Phase 2

SMELL-007 and SMELL-023 no longer fire. Only STRUCT-011 (no
pyproject.toml) and OPS info-level findings remain.

---

## Phase Roadmap

### Phase 0 — reference exemplars (8/8 COMPLETE)

- [x] All eight schools: Classical, Pragmatic, Functional, Unix,
  Convention, Resilient, Data-Oriented, Event-Sourced

### Phase 1 — engine change (COMPLETE)

### Phase 2 — detector precision fixes (8/9 COMPLETE)

- [x] DOM-001 Manager awareness (#173) + generic type support (#174)
- [x] STAB-001 chain-terminal handling (#173)
- [x] DJ-SEC-001 test-placeholder skip (#174)
- [x] SEC-003 test-prefix detection (#174)
- [x] SCHEMA-001 reference-data exemption (#175)
- [x] SEC-001 security-sensitive models only (#175)
- [x] SMELL-007 injected-dep exemption (#176)
- [x] SMELL-023 Protocol awareness (#176)
- [~] SMELL-008 ShotgunSurgery — addressed by exemplar, not detector

### Phase 3 — polish (next)

- CLI attribution in report output (show which philosophy a rule
  belongs to when it fires)
- `gaudi philosophy --explain` deterministic inference from project
  dependencies
- Website audit: run `gaudi check` against Nathan's real Django
  website, categorize findings, surface audit gaps driven by
  production evidence

---

## Things To Know Before Next Session

1. **PRs merged this session (4 total)** — all on main:
   - #173 DOM-001 Manager awareness + STAB-001 chain-terminal
   - #174 DOM-001 generic Manager + DJ-SEC-001/SEC-003 test placeholders
   - #175 SCHEMA-001 reference-data + SEC-001 sensitive-models-only
   - #176 SMELL-007 injected-dep + SMELL-023 Protocol awareness

2. **The RFC file** `gaudi-architectural-philosophies.md` in the
   repo root is still untracked. Safe to delete or move to docs/.

3. **Python environment note**: the Oversteward conda env's pip
   resolves to the ai-assistants env's pip. To install packages in
   Oversteward, use `conda run -n Oversteward python -m pip install`
   (not bare `pip install`). The editable install was refreshed
   this session via `python -m pip install -e ".[dev]"`.

4. **The highest-value next session** is Phase 3 polish:
   - **Option A: CLI attribution** — when a finding fires, show
     which philosophy school it belongs to. Useful for understanding
     why a rule fires under one school but not another.
   - **Option B: `gaudi philosophy --explain`** — infer the project's
     philosophy from its dependencies (Django → convention, no
     framework → classical/pragmatic, etc.).
   - **Option C: Website audit** — run gaudi against Nathan's real
     Django site, categorize findings, identify gaps.
   - **Option D: Clean up RFC file** — delete or move
     `gaudi-architectural-philosophies.md`.

5. **Two "correct" findings remain on Convention exemplar:**
   - DOM-001 on Notification (genuinely anemic, 5 fields, no Manager)
   - SCHEMA-001 on OrderLine (has FKs, no timestamps)
   These are working-as-intended and document real architectural
   choices the Convention exemplar makes.

---

## Test Suite / Build Status

- `ruff check .` — clean
- `ruff format --check .` — clean
- `pytest --tb=short -q` — **722 passed**
- `gaudi check` on Convention exemplar — 0 errors, 12 warnings, 13 infos
- `gaudi check` on Classical exemplar — 0 errors, 1 warning, 5 infos
- CI: every PR this session merged green without `--admin`

---

## Commits Landed (this session, in order)

```
687b3d2 fix(rules): SMELL-007 injected-dep exemption + SMELL-023 Protocol awareness (#176)
502cab5 fix(rules): SCHEMA-001 reference-data exemption + SEC-001 sensitive-models-only (#175)
26252ad fix(rules): DOM-001 generic Manager + DJ-SEC-001/SEC-003 test placeholders (#174)
9bade4b fix(rules): DOM-001 Manager awareness + STAB-001 chain-terminal handling (#173)
```

Branch tip: `main`. No open PRs. No uncommitted changes other than
the untracked RFC file.
