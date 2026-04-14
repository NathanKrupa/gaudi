# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] — 2026-04-14

### Added
- **OWASP Top 10 structural slice** — new security rules covering
  deserialization, weak crypto, SSL verification, XXE, insecure tempfiles,
  subprocess shell injection, and path traversal (#142, #202–#205)
- **SEC-006 SSRFVector** — intra-procedural taint tracking for server-side
  request forgery vectors (#196)
- **`gaudi cheat-sheet` command** — generates rule cheat-sheet from the live
  registry (#130)
- **SMELL-025 TemporalIdentifier** — flags temporal markers ("new", "old",
  "legacy", "v2") in identifiers (#131)
- **Drift guard** — CI check that `docs/gaudi-rules.md` matches
  `gaudi cheat-sheet` output (#133)
- **Vacuous-pass detection** for the fixture corpus — catches fixtures where
  the rule was never activated (#99)
- **Activation visibility logging** — surfaces which rules activated per file
  and why (#112)
- **DEP pack boundary fixtures** — replaces legacy `test_dependency_rules.py`
  with fixture-first coverage (#101)

### Fixed
- **LOG-002** — tightened sensitive-name matching to reduce false positives (#129)
- **SVC-004** — corrected app detection so top-level dirs of one project are
  not treated as separate apps (#149)
- **ARCH-011** — guard patterns prevent parser/cache decisions from being
  misclassified as business logic (#154)
- **PYD-ARCH-001** — no longer fires on `model_config` class variable (#148)
- **ARCH-001** — multi-tenant rule now opts in instead of firing on
  non-tenant projects (#150)
- **Ops pack** — supports Dockerfile stage variants (Dockerfile.prod,
  app.Dockerfile) (#140)
- Shared `collect_receiver_names` helper replaces duplicated inline
  implementations (#199)

### Changed
- **Project environment** switched from Oversteward conda env to project-local
  `.venv/` (#103)
- Rule keying and activation gates hardened after fixture migration (#112)

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
