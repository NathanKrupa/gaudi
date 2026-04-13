# Changelog

All notable changes to this project will be documented in this file.

## [0.1.2] — 2026-04-13

### Added
- **Philosophy attribution** in all output formats — scoped rules show
  which schools they apply to (e.g., `DOM-001 [WARN] (classical, convention)`)
- **`gaudi philosophy` command** — infers which architectural school best
  matches a project from its dependencies and structure
- **Severity overrides** from `[gaudi.rules]` in gaudi.toml — map rule
  codes to severity levels or `"off"` to suppress entirely
- **Inline `# noqa` suppression** — `# noqa: RULE-ID` suppresses specific
  findings per line; bare `# noqa` suppresses all findings on a line
- **Editorial doctrine section** in CONTRIBUTING.md referencing docs/principles.md

### Fixed
- **DOM-001** false positives on Django models with generic Manager types
  (`Manager["Model"]`)
- **DJ-SEC-001** false positives on test-placeholder SECRET_KEY values
- **DJ-SEC-002** false positives on local/dev settings files (`DEBUG = True`)
- **SEC-003** false positives on test-prefixed credential values
- **SMELL-005** false positives on Django `urlpatterns` (module-level list by design)
- **SMELL-007** false positives on coordinator/service classes with injected
  dependencies
- **SMELL-023** false positives on Protocol classes (stub methods are interface
  declarations, not refused bequests)
- **SCHEMA-001** false positives on reference/lookup models (no ForeignKey,
  no mutable-state fields)
- **SEC-001** noise on ordinary Django models — now only fires on
  security-sensitive model names/paths
- **STAB-001** noise from `.filter()`, `.select_related()`, `.exclude()`,
  `.prefetch_related()` — only `.all()` triggers unbounded result set warnings
- **PY314-006** false positives on non-tarfile `.extractall()` calls
- **SMELL-003** threshold raised from 25 to 30 lines to reduce noise on
  normal-complexity methods

### Changed
- **Migrations no longer excluded by default** — Django migration files can
  contain architecture issues and should be linted. Add `"**/migrations/**"`
  to `[gaudi].exclude` in gaudi.toml if you want to restore the old behavior.
- School configuration passed from CLI through engine to packs, so
  `[philosophy].school` in gaudi.toml is respected in all invocations

### Removed
- RFC file moved from repo root to `docs/gaudi-architectural-philosophies.md`

## [0.1.1] — 2026-04-08

### Added
- Philosophy scoping system (Rule.philosophy_scope, [philosophy].school in gaudi.toml)
- 8 reference exemplars (Classical, Pragmatic, Functional, Unix, Convention,
  Resilient, Data-Oriented, Event-Sourced)
- Philosophy matrix acceptance tests (206 tests)

## [0.1.0] — 2026-04-07

Initial alpha release. Python-only architecture linter with ~124 rules.
