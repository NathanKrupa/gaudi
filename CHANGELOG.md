# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed

- **`--exit-code` now gates at the severity `--severity` selected** (#267).
  It counted error-severity findings only, whatever threshold the caller
  asked for, so `gaudi check . --severity warn --exit-code` exited `0` with
  96 warnings on the report — a gate that could not fail. The flag names a
  threshold; it now honours it.

### Migration

- **`--exit-code` paired with `--severity error` is unchanged.** That is the
  documented shape, and every example in this repo, its CI, and
  `docs/llm-workflow.md` already uses it.
- **`--exit-code` paired with `--severity warn` or `--severity info` will now
  go red where it was silently green.** That is the fix, not a regression: the
  run was failing the threshold all along and reporting success.
- **Bare `--exit-code` with no `--severity` now gates at `info`,** because
  `info` is the default reporting threshold. A gate that wants the old
  behaviour must say what it always meant: `--severity error --exit-code`.

## [0.3.0] — 2026-09-02

The overhaul release (#256). A 2026-08-31 estate audit measured what Gaudi was
actually doing across two production repos: the **error tier earns its keep**
(zero `sys.path` hacks and zero dependency cycles at HEAD across 2,700 files;
three real security fixes from SEC-012), while the **warn tier was ~50% churn
and ~19% harm** — ratchet payments that relocated a production guard out of the
function enforcing it, deleted a shared SSRF sink, and deleted three
explanatory comments to get a function under a line count.

Three things follow from that, and this release is all three: make the
instrument honest about what it did not measure; separate the rules that name
debt from the rules that name idiom; and aim the rule set at defects the estate
actually ships rather than at shapes that are merely countable.

### Migration

- **`--exit-code` gained exit status 2** — "at least one file could not be
  parsed". A gate that treats any non-zero as failure needs no change. A gate
  that tests `-eq 1` must be widened, and a gate that was silently green over
  unparsable files will now go red: that is the fix, not a regression.
- **STRUCT-021 and CPLX-002 moved from `warn` to `info`.** A `--severity warn`
  report shrinks accordingly. Baselines counted against the *total* finding
  count will drop; use `gaudi count --ratchet` instead, which counts the named
  debt set and is stable across tier changes.
- **`gaudi.toml` is now found by walking up to the project root.** A repo that
  carries per-app copies to work around the old behaviour can delete all but
  the root one — but check first that the copies were identical, because the
  nearest one now wins.
- **`noqa` accretions the precision pass obsoletes.** Each of these can be
  removed from consuming repos once they upgrade; none is removed here (the
  drop is per-repo work):

  | rule | suppressions this release makes unnecessary |
  | --- | --- |
  | STAB-001 | queries bounded by `.limit(n)` or `[:n]` (~10 sites in grantspider) |
  | SVC-004 | `from django.db.models import Count, Q` and siblings (aigranthelper) |
  | SEC-002 | `SET statement_timeout = …` and other SET-statement hits |
  | SEC-003 | constants holding a file path whose name contains a credential word |
  | SMELL-025 | local variables named `new`, `new_items`, and the like |
  | STAB-011, SVC-006 | repo-wide disables added because per-file mode stripped the project context — both are now excluded from single-file runs automatically |

### Added
- **Skip accounting** (#256). A file the parser cannot read — a syntax the
  running interpreter is too old for, an unreadable path — is now reported and
  counted instead of silently dropped. `text` output prints a skip block naming
  each file and its reason, `--format json` gains a `skipped` list, and
  `--format github` annotates the file on the diff. Under `--exit-code` a skip
  exits **2**, distinct from findings (1) and clean (0), and outranks findings:
  a run that could not look everywhere is incomplete whatever else it reported.
  This closes a false green — an estate error gate on ~36 files whose PEP 758
  syntax the installed 3.11 interpreter could not parse exited 0 with output
  identical to a clean run.
- `Engine.check_result()` and `Pack.check_result()` return findings alongside
  the skipped files; `check()` still returns findings only.
- `Rule.requires_project_context` — a rule whose clearing evidence lives in a
  sibling file declares it, and packs sit that rule out of single-file
  invocations rather than firing unconditionally. Set on **STAB-011** (health
  route pooled across the project) and **SVC-006** (paired test module), the
  two rules aigranthelper had disabled repo-wide for exactly this reason.

- **`gaudi count`** (#228) — findings per rule code, machine-readable. Text
  output is a bare integer (`baseline=$(gaudi count . --ratchet)`); `--format
  json` emits a `{code: count}` map. `--code CODE` counts one rule;
  `--ratchet` counts only the debt set (`DEP-001`, `DEP-004`, `SMELL-003`,
  `SMELL-007`, `STAB-006`), so repos stop hand-building the filter and stop
  counting style-tier findings as debt. Exit **2** when any file was skipped:
  the number printed is then an undercount, and a ratchet comparing it against
  a complete baseline would read the missing findings as progress.

- **SA-ARCH-001 TransactionBoundaryIO** (#256 item 2) — an `error`-severity
  rule firing on a network call (`requests` / `httpx` / `urllib` / `urllib3`)
  inside a SQLAlchemy or psycopg transaction block (`with session.begin():`,
  `with engine.begin() as conn:`, `with conn.transaction():`). DJ-ARCH-004 asks
  the same question of Django's `transaction.atomic()`, so a SQLAlchemy repo
  was never asked it at all: grantspider has 0 `atomic()` blocks and 43
  explicit `.commit()` calls, and both of its transaction incidents (a four-day
  CRASHED service; 357 rows of paid model output lost) were structurally
  invisible. Scope is deliberately shallow — `with`-block bodies only, no
  dataflow. DJ-ARCH-004 gains `urllib` coverage from the shared helper.

### Fixed
- **Project-level questions resolve against the project root** (#256 items 7
  and 10). `gaudi check apps/billing` in a packaged repo reported STRUCT-011
  ("no pyproject.toml") and STRUCT-013 ("no lock file") because both rules
  looked only at the path passed to `check`. They now resolve the project root
  by walking up to the nearest packaging marker or `.git`. `gaudi.toml` is
  found the same way, bounded at the project root so a config outside the
  project is never adopted by it — this is why one estate repo carried six
  app-scoped copies of it.
- **STRUCT-013 recognises `uv.lock`** as a dependency lock file.
- **SEC-002** no longer fires on `SET <parameter> = {value}` (#256 item 8).
  Postgres accepts no bind parameter in `SET`, so there is no parameterized
  form to recommend and every estate hit was a cosmetic hoist of the same
  f-string. The parameter *name* must be literal: `SET {name} = 5` interpolates
  the identifier and still fires.
- **SEC-003** no longer treats a filesystem path as a credential (#256 item 6).
  `SECRET_SCAN_SCRIPT = "scripts/dev/secret_scan.py"` names a tool; one estate
  repo renamed a constant purely to dodge the finding.
- **SMELL-025** no longer fires on a local variable (#256 item 6). Its subject
  is names that outlive the moment they are written — classes, functions,
  module and class attributes — which is what its docstring always said while
  it walked every assignment in the file. `new = tuple(i for i in issues if i
  not in ruled)` inside a function is the ordinary English adjective;
  `new_billing_handler` as a function name still fires.
- **STAB-001** recognises `.limit(n)` and slicing (`[:n]`) as bounding (#245).
  The rule's own recommendation says "Add `.limit()`", so following its advice
  did not clear it — ten sites across one estate repo carried a permanent
  `# noqa: STAB-001` for correctly-bounded queries.
- **SVC-004** no longer treats framework `models` modules as project apps
  (#214). `from django.db.models import Count, Q` was read as app `db` owning
  models `Count` and `Q`, making every app that aggregates a coupled consumer
  of it.
- **ERR-003** now keys on the swallow rather than on the log level (#256 item
  1). `except …:` that logs at *any* level and does not re-raise fires;
  previously only `error` and `exception` did. One estate repo carried 127
  warning-logged swallows against 17 error-logged — the rule was blind to 88%
  of its own population, which is how an unreadable object-store read was
  logged at warning, read as "the site says nothing", and stamped 30-day empty
  sentinels across an outage. A handler that logs nothing stays out of scope:
  ERR-001 and ERR-004 own it. The message now says "Exception logged but not
  re-raised" rather than "Error logged …", since the level is no longer the
  subject.
- `is_logger_call` / `LOG_METHODS` moved to
  `packs/python/ast_helpers.py`; `logging_rules.py` and `errors.py` share one
  definition of what a logger call is.

### CI
- **Gaudi runs Gaudi on Gaudi.** The `lint` job runs
  `gaudi check src/ --severity error --exit-code`. Verified in both directions
  before merge: clean on the tree as it stands, exit 1 with an injected
  `sys.path` hack, exit 2 with an injected unparsable file. The error tier is
  the gate; warn and info are reported and discussed, never gated — which is
  the distinction this whole release exists to draw.

### Documentation
- The distribution is `gaudi-linter`; the command is `gaudi`. `pip install
  gaudi` fetches an unrelated project. Named correctly in CONTRIBUTING.md,
  CLAUDE.md and the `list-packs` hint (#256 hygiene).
- `docs/llm-workflow.md` documented `# noqa: gaudi(<CODE>)`, which the parser
  never matched — it silently suppressed nothing. Replaced with the real
  syntax and a suppression-forms table (#225).
- The SEC import-resolution helpers no longer claim to be shared by two rules
  when four use them (#226).
- CLAUDE.md records why a worktree must invoke `python -m gaudi.cli` with an
  absolute `PYTHONPATH` rather than the console script: the shebang is absolute
  and `language: system` pre-commit hooks resolve `gaudi` from `PATH`, so both
  can measure a different checkout than the one being edited.

### Changed
- **STRUCT-021** and **CPLX-002** demoted from `warn` to `info` (#256 items 4
  and 5). Both are style-tier: STRUCT-021's count threshold cannot tell a magic
  string from a Django field name or the literal a test asserts on (58% of one
  estate repo's warnings), and CPLX-002 fires on the explicit parameter
  threading config-injection architecture prescribes (that repo's
  most-suppressed rule, 54 `noqa`). They stay in the catalog and stay
  reportable; `--severity warn` no longer surfaces them. SMELL-025 was already
  `info` and is unchanged.

## [0.2.2] — 2026-06-19

### Fixed
Rule-precision pass on the false-positive cluster (#239) — each rule keeps
catching genuine violations but stops firing on a by-design pattern, so repos
can drop the corresponding `# noqa` accretions:

- **DOM-001** — exempt intentional telemetry/event/value tables (names ending
  in event, impression, log, audit, metric, snapshot, feedback, ...). Their
  behavior belongs to the aggregator that reads them.
- **ARCH-003** — require the true join-table shape (only ForeignKeys, no other
  fields). A first-class entity with two optional FKs plus real fields no
  longer fires.
- **IDX-001** — don't fire on a lookup column already served by a covering
  composite index (leading column of `Meta.indexes` / `index_together` /
  `unique_together`).
- **ARCH-011** — exempt connector parse-layer dispatch (branching on an XML
  element tag, an XPath hit, or a parser method result is format translation,
  not a business decision).
- **SMELL-025** — exempt a constant whose version-suffix name pins its string
  value (`SCHEMA_V1 = "v1"`): a persisted/DB-pinned literal, not change history.
- **SEC-003** — distinguish an env-var NAME constant (`API_KEY_ENV =
  "MYAPP_API_KEY"`, or any UPPER_SNAKE env-var-name value) from a literal
  secret.
- **PYD-ARCH-001** — don't fire on `ClassVar`-annotated attributes; these are
  class attributes, not per-instance defaults.
- **STRUCT-010** — exempt executable entrypoints (files under scripts/bin/tools,
  manage.py / conftest.py, or files with an `if __name__ == "__main__":` guard)
  that bootstrap `sys.path` to locate siblings before install.

## [0.2.1] — 2026-06-19

### Fixed
- **STAB-011** — made the missing-health-endpoint check root-URLConf-aware.
  Django projects mount one root URLConf (named by `ROOT_URLCONF`, e.g.
  `config/urls.py`) plus many included app URLConfs; only the root owns
  `/health`. The rule now evaluates health against the root URLConf alone,
  so included app `urls.py` files are no longer false-positives while a
  genuinely missing health endpoint on the root still flags.

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
