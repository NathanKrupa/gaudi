# AIgranthelper Django Audit — 2026-04-12

**Project:** `C:\Users\natha\OneDrive\Tech\Python\aigranthelper`
**Philosophy:** convention (Django — inferred by `gaudi philosophy`)
**Gaudi version:** 0.1.1 (post-Phase 4)

---

## Summary

| Severity | Count |
|---|---|
| Error | 20 |
| Warning | 504 |
| Info | 180 |
| **Total** | **704** |

Findings exclude `.claude/worktrees/` (agent scratch copies) and
migration files. Raw unfiltered total across 160 files: 1,475.

---

## Top Findings by Rule

| Rule | Count | Severity | Category |
|---|---|---|---|
| STRUCT-021 MagicStrings | 189 | warn | Repeated string literals |
| SVC-004 | 75 | warn | Service layer |
| STRUCT-020 | 67 | info | Structure |
| STAB-001 UnboundedResultSet | 55 | warn | Unbounded ORM queries |
| SMELL-003 LongFunction | 45 | warn | Functions >50 lines |
| IDX-002 | 44 | info | Missing date field indexes |
| SCHEMA-003 | 34 | info | Schema |
| DOM-001 AnemicDomainModel | 29 | warn | Fields with no behavior |
| CPLX-002 | 21 | warn | Complexity |
| SMELL-005 MutableModuleVar | 19 | error | Module-level mutables |
| SMELL-009 | 18 | warn | Code smell |
| ARCH-002 | 11 | warn | Architecture |

---

## Detector Precision Issues Surfaced

### 1. SMELL-005 fires on Django `urlpatterns` (9 of 19 findings)

**False positive.** Django's `urlpatterns = [path(...)]` in every `urls.py`
is the blessed idiom. SMELL-005 treats this as a mutable module-level
variable, but Django requires it to be a module-level list.

**Fix:** SMELL-005 should exempt `urlpatterns` by name, or exempt any
module-level list assignment in files named `urls.py`.

### 2. STAB-001 fires on `.select_related()` and `.filter()` in services

STAB-001 fires on 55 lines. Many are ORM queries in service layers that
eventually terminate in `.first()`, iteration inside a paginated view, or
are consumed by Django templates with pagination. The Phase 2 fix for
`.first()` and `.get()` chain terminals helped, but `.select_related()`
as a standalone call and `.filter()` followed by a for loop are still
flagged.

**Possible improvement:** Track whether the result is consumed by a
paginated view helper or a `[:N]` slice.

### 3. DJ-SEC-002 fires on `local.py` settings

**Debatable.** `config/settings/local.py` has `DEBUG = True` — that's
correct for local dev settings. The rule could exempt files with "local",
"dev", or "development" in the path.

### 4. DOM-001 on Django models — many are legitimately anemic

The 29 DOM-001 findings are split:
- Models with custom Managers (Manager awareness should catch these — check
  if Manager["Model"] generic form is being used in aigranthelper)
- Models that genuinely have no behavior — these are correct findings.
  Django's convention says business logic goes on Managers or in services,
  so many Convention-school models will be anemic by design.

**Implication:** Under `school = "convention"`, DOM-001 might be too
aggressive. Consider adding a higher field threshold for Convention school
or scoping DOM-001 away from Convention entirely.

---

## High-Value Actionable Findings

These are findings that represent real architectural opportunities, not
noise:

1. **SMELL-003 (45 long functions)** — 45 functions over 50 lines.
   Worth reviewing the top offenders for extraction opportunities.

2. **CPLX-002 (21 complexity findings)** — High cyclomatic complexity
   in key modules. Check pipeline and research apps.

3. **ARCH-002 (11 findings)** — Architectural boundary violations.
   Worth investigating cross-app imports.

4. **ERR-001/ERR-003/ERR-004 (20 total)** — Error handling issues.
   Bare excepts, missing error context, swallowed exceptions.

5. **LOG-004 (5 findings)** — Logging issues worth reviewing.

---

## Recommended gaudi.toml for AIgranthelper

```toml
[gaudi]
exclude = [
    ".claude/**",
    "*/migrations/**",
    "data/**",
    "local_storage/**",
]

[gaudi.rules]
# Django urlpatterns are module-level lists by design
SMELL-005 = "warn"

# Magic strings are noisy in Django templates/admin
STRUCT-021 = "info"

# Local settings legitimately have DEBUG = True
# DJ-SEC-002 = "off"  # uncomment if too noisy

[philosophy]
school = "convention"
```

---

## Next Steps for Gaudi

Precision improvements surfaced by this audit:

1. **SMELL-005 urlpatterns exemption** — Exempt `urlpatterns` in `urls.py`
2. **DJ-SEC-002 local settings exemption** — Skip files with "local" or
   "dev" in the path
3. **STAB-001 pagination awareness** — Consider slice/pagination as
   bounded consumption
