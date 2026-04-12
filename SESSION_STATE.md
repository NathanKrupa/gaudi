# Session State — Gaudi

## Last Updated
2026-04-12 (Phase 4 complete + AIgranthelper Django audit)

## Current Status
Alpha (v0.1.1). Python-only architecture linter.
~124 implemented rules, 23 scoped to specific schools, ~101 universal.
**Phase 0-4 complete.** All planned features shipped.

Test suite: **760 passed**. Ruff clean.

---

## What Changed This Session

Phase 4 (severity overrides + noqa) shipped and first real-world
Django audit completed against AIgranthelper.

### Phase 4 — Engine features (PR #182)

**Severity overrides from gaudi.toml:**
```toml
[gaudi.rules]
SMELL-003 = "error"   # promote
IDX-001 = "off"       # suppress
```

**Inline noqa suppression:**
```python
x = "magic"  # noqa: STRUCT-021
y = "magic"  # noqa           (suppresses all)
```

Implementation: config.py parses `[gaudi.rules]`, engine applies
overrides post-collection, PythonPack filters noqa per-line during
rule execution.

### AIgranthelper Django Audit

Full audit report: `docs/audits/aigranthelper-2026-04-12.md`

**Key numbers:** 704 findings (20 errors, 504 warnings, 180 infos)
across ~80 files (excluding .claude worktrees and migrations).

**Detector precision issues surfaced:**
1. SMELL-005 fires on Django `urlpatterns` (9 false positives)
2. DJ-SEC-002 fires on `local.py` dev settings
3. STAB-001 noisy on `.select_related()` chains

**High-value actionable findings:**
- 45 long functions (SMELL-003)
- 21 complexity hotspots (CPLX-002)
- 11 architecture boundary violations (ARCH-002)
- 20 error handling issues (ERR-001/003/004)

---

## Phase Roadmap — All Complete

- **Phase 0:** 8/8 reference exemplars
- **Phase 1:** Engine (philosophy_scope + gaudi.toml school filtering)
- **Phase 2:** 8/9 detector precision fixes
- **Phase 3:** CLI polish (attribution, inference, RFC archive)
- **Phase 4:** Severity overrides + noqa + first production audit

### Next candidates

- **SMELL-005 urlpatterns exemption** — Django `urlpatterns` is a list by design
- **DJ-SEC-002 local settings exemption** — Skip "local"/"dev" settings files
- **STAB-001 pagination awareness** — Sliced/paginated queries are bounded
- **Rule documentation** — Auto-generated docs per rule

---

## Things To Know Before Next Session

1. **PR merged this session:** #182 (severity overrides + noqa)

2. **AIgranthelper audit** lives at `docs/audits/aigranthelper-2026-04-12.md`
   with recommended gaudi.toml config for that project.

3. **Python environment**: Oversteward conda env, editable install.

4. **No open PRs.** All work merged to main.

---

## Test Suite / Build Status

- `pytest --tb=short -q` — **760 passed**
- `ruff check .` + `ruff format --check .` — clean
- CI: all PRs merged green without `--admin`

---

## Commits Landed (this session)

```
c7de93d feat(engine): severity overrides + inline noqa suppression (#182)
```
