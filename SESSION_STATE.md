# Session State -- Gaudi

## Last Updated
2026-04-06

## Current Status
Alpha (v0.1.0). Python-only architecture linter. PyPI package name: `gaudi-linter`.
79 rules: 64 general + 15 library-specific across 10 libraries.
Library activation system auto-detects project dependencies.

## What Changed This Session
1. Added rule source registry (`docs/rule-registry.md`) mapping all rules to canonical texts
2. Added 6 Nygard stability rules (STAB-001, 003-007) from *Release It!* (2nd ed.)
3. Added 3 Newman service boundary rules (SVC-001-003) from *Building Microservices* (2nd ed.)
4. Added STABILITY category to core.py
5. Implemented library activation system:
   - `Rule.requires_library` attribute for library-specific rules
   - `PythonContext.detected_libraries` from pyproject.toml/requirements.txt/imports
   - `PythonPack.check()` filters rules by detected libraries
   - All 15 library rules tagged with `requires_library`
6. Removed 5 redundant rules after audit:
   - STAB-002 (NoCircuitBreaker): detection too weak
   - HTTP-ARCH-001 (RequestsNoRetry): subsumed by STAB-003
   - SA-ARCH-001 (SQLAlchemySessionLeak): consolidated into STAB-006
   - DJ-STRUCT-001 (DjangoFatView): covered by SMELL-003/SMELL-020
   - FAPI-SCALE-001 (FastAPISyncEndpoint): covered by STAB-005

## Project Structure
```
src/gaudi/
  core.py              # Finding, Rule, Severity, Category (+ STABILITY, requires_library)
  engine.py            # Pack discovery and orchestration
  pack.py              # Base Pack class
  packs/python/
    context.py         # PythonContext (+ detected_libraries)
    pack.py            # PythonPack (+ library-filtered check())
    parser.py          # AST parser (+ _detect_libraries())
    rules/
      __init__.py      # ALL_RULES aggregation
      architecture.py  # ARCH/IDX/SCHEMA/SEC/STRUCT (10 rules)
      smells.py        # SMELL-001 to SMELL-024 (24 rules)
      arch90.py        # STRUCT/ARCH/ERR/LOG/OPS (15 rules)
      stability.py     # STAB-001,003-007 (6 rules) [Nygard]
      services.py      # SVC-001 to SVC-003 (3 rules) [Newman]
      py314.py         # PY314-001 to PY314-006 (6 rules)
      django.py        # DJ-SEC-001, DJ-SEC-002 (requires_library="django")
      fastapi.py       # FAPI-ARCH-001 (requires_library="fastapi")
      sqlalchemy.py    # SA-SCALE-001 (requires_library="sqlalchemy")
      flask.py         # FLASK-STRUCT-001 (requires_library="flask")
      celery.py        # CELERY-ARCH-001, CELERY-SCALE-001 (requires_library="celery")
      pandas.py        # PD-ARCH-001, PD-SCALE-001 (requires_library="pandas")
      requests_rules.py # HTTP-SCALE-001 (requires_library="requests")
      pydantic.py      # PYD-ARCH-001 (requires_library="pydantic")
      pytest_rules.py  # TEST-STRUCT-001, TEST-SCALE-001 (requires_library="pytest")
      drf.py           # DRF-SEC-001, DRF-SCALE-001 (requires_library="drf")
docs/
  rule-registry.md     # All rules mapped to canonical sources + mining queues
```

## Open PRs
- #35: Add stability/service rules, library activation, rule registry

## Rule Source Texts
- **FOWLER**: Refactoring (2nd ed.) -- 24 SMELL rules
- **NYGARD**: Release It! (2nd ed.) -- 6 STAB rules
- **NEWMAN**: Building Microservices (2nd ed.) -- 3 SVC rules
- **ARCH90**: Architecture 90 curriculum -- 15 rules
- **PY314**: CPython 3.14 changelog -- 6 rules
- **FWDOCS**: Framework documentation -- 15 library rules

## Next Steps
1. Mine Ousterhout (*A Philosophy of Software Design*) for complexity rules (CPLX-???)
2. Mine Fowler PEAA for domain model rules (DOM-???)
3. Wire gaudi.toml config overrides into library activation (include/exclude)
4. PyPI publishing setup (trusted publisher on pypi.org)
5. Increase test coverage for architecture.py and py314.py rule files
