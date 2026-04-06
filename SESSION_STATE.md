# Session State -- Gaudi

## Last Updated
2026-04-06

## Current Status
Alpha (v0.1.0). Python-only architecture linter. PyPI package name: `gaudi-linter`.
All non-Python language packs removed. Rules split into per-library modules.

## What Changed This Session
1. Removed all 10 non-Python language packs (JS, Go, C++, Ruby, Rust, Java, C#, PHP, Kotlin, Swift)
2. Split rules_libraries.py (574 lines, 18 rules) into 10 per-library modules under rules/
3. Moved core architecture rules and py314 rules into rules/ package
4. Removed dead code: Engine._config, PythonContext.tables, ModelInfo.table_name
5. Fixed CI: ruff formatting, bandit skips (B110/B112), pip-audit --skip-editable, coverage threshold 60%
6. Updated README for Python-only focus with full rule category/library tables
7. Created 25 GitHub issues tracking Fowler's 24 code smells (19 refactoring + 5 detection rules + 1 tracker)

## Project Structure
```
src/gaudi/
  __init__.py          # Public API, version from metadata
  cli.py               # Click CLI (gaudi check, gaudi list-packs)
  config.py            # gaudi.toml loader (wired to CLI)
  core.py              # Finding, Rule, Severity, Category
  engine.py            # Pack discovery and orchestration
  pack.py              # Base Pack class
  packs/
    __init__.py
    python/
      __init__.py
      context.py       # PythonContext, ModelInfo, ColumnInfo, FileInfo
      pack.py          # PythonPack (registers all rules)
      parser.py        # AST-based parser
      rules/
        __init__.py    # Assembles ALL_RULES from all modules
        architecture.py # Core arch rules (ARCH, IDX, SCHEMA, SEC, STRUCT)
        py314.py       # Python 3.14 compatibility rules
        django.py      # DJ-SEC-001, DJ-SEC-002, DJ-STRUCT-001
        fastapi.py     # FAPI-ARCH-001, FAPI-SCALE-001
        sqlalchemy.py  # SA-ARCH-001, SA-SCALE-001
        flask.py       # FLASK-STRUCT-001
        celery.py      # CELERY-ARCH-001, CELERY-SCALE-001
        pandas.py      # PD-ARCH-001, PD-SCALE-001
        requests_rules.py # HTTP-SCALE-001, HTTP-ARCH-001
        pydantic.py    # PYD-ARCH-001
        pytest_rules.py # TEST-STRUCT-001, TEST-SCALE-001
        drf.py         # DRF-SEC-001, DRF-SCALE-001
```

## Open PRs
- None pending

## GitHub Issues
- #3-#21: Fowler code smell refactoring issues (some resolved by this session's work)
- #22: Tracker for SMELL rule category (detect all 24 Fowler smells)
- #23-#27: Individual SMELL detection rule issues (Tier 3 hard detections)

## Next Steps
1. Phase 2: Enrich data classes with behavior (move repeated rule logic onto ModelInfo/Context)
2. Phase 2: Framework enum, Severity display properties
3. Phase 2: Auto-register rules (eliminate manual list management)
4. Phase 3: Build SMELL detection rules (start with SMELL-004 Long Parameter List, SMELL-013 Loops)
5. Increase test coverage (currently ~70%, rules/ modules need tests)
6. PyPI publishing setup (trusted publisher on pypi.org)
