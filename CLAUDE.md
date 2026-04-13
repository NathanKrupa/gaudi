@~/.claude/shared/souls/chestertron.md

At session start, check `~/.claude/shared/inbox.md` for updates. If entries exist, review them and apply any relevant changes, then clear the file.
---

# Working Guidelines

Core rules: `~/.claude/CLAUDE.md`

---

# Project-Specific Configuration

## Python Environment

Use the project-local venv at `.venv/`:
```bash
.venv/Scripts/python.exe -m pytest
.venv/Scripts/gaudi.exe check .
```

First-time setup: `python -m venv .venv && .venv/Scripts/pip.exe install -e ".[dev]"`

## Principles

**Editorial doctrine for this project:** [docs/principles.md](docs/principles.md).
Fourteen numbered principles in three pillars (Truthfulness, Economy, Cost-honesty)
that govern which rules enter the catalog, how thresholds and severities are
assigned, and when a rule should be cut. Every design question in this project
must appeal to a principle. If no principle decides it, the doctrine has a gap
and the question warrants discussion, not a coin flip.

## Architecture

Personal coding doctrine: `@~/.claude/shared/references/architecture-principles.md`
(layer model — outer/middle/inner). The Gaudi-specific principles in
[docs/principles.md](docs/principles.md) extend and supersede this for any
Gaudi rule decision.

**Layer map for this project:**
- **OUTER:** `src/gaudi/cli.py` (CLI entry point), future scripts
- **MIDDLE:** `src/gaudi/engine.py` (orchestration), `src/gaudi/pack.py` (base class), `src/gaudi/config.py` (configuration)
- **INNER:** `src/gaudi/core.py` (data models: Finding, Rule, Severity, Category), `src/gaudi/packs/` (language-specific implementations)

## Key Components

- **src/gaudi/core.py** — Data models: Finding, Rule, Severity, Category enums, `requires_library` activation
- **src/gaudi/engine.py** — Pack discovery via entry points, orchestration
- **src/gaudi/config.py** — TOML config loader (gaudi.toml)
- **src/gaudi/cli.py** — Click-based CLI (`gaudi check`)
- **src/gaudi/packs/python/** — Python language pack (79 rules: 64 general + 15 library-specific)
- **tests/** — pytest suite with fixtures
- **docs/rule-registry.md** — Maps every rule to its canonical source text

## Key Files

- **README.md** — User-facing documentation
- **CONTRIBUTING.md** — Contributor guide
- **pyproject.toml** — Package metadata, dependencies, entry points, ruff config
- **gaudi.toml** — Runtime configuration (severity overrides, exclusions)
- **docs/rule-registry.md** — Rule provenance and mining queues

## PR Workflow

**Every piece of work flows through a PR. PRs are the project's task board.**

1. **Define scope first.** Open an issue or write a PR description BEFORE writing code. The description is the contract — if implementation outgrows it, stop and split.
2. **One PR = one logical change.** "Add Nygard stability rules" is one PR. "Add stability rules + service rules + library activation + redundancy audit" is four PRs crammed into one. Split them.
3. **Branch naming:** `feat/short-description`, `fix/short-description`, `docs/short-description`.
4. **Never commit directly to main.** Branch protection enforces this.
5. **Never use `--admin` to bypass CI.** Wait for checks. The 30 seconds is worth the discipline.
6. **Draft PRs for exploration.** If you're not sure of scope yet, open a draft. Convert to ready when scope is clear.
7. **PR description template:** Summary (what + why), test plan (how verified). The `.github/pull_request_template.md` enforces this.

**Scope check before starting work:** Before writing code, state: (a) the branch name, (b) the PR title, (c) 1-3 bullet scope description. If you can't state these clearly, the work isn't scoped yet.

## Open Source Project

Gaudi is MIT-licensed and intended for public contribution. When working on this project:
- Write clear commit messages suitable for public history
- All code must include type hints on public APIs
- Follow the existing Click CLI patterns for any new commands
- Keep dependencies minimal — this runs in other people's CI pipelines

## Fixture-First TDD (Mandatory for Rules)

**Every new or changed rule MUST start from a fixture.** No exceptions.

The full rubric lives in [docs/testing-fixtures.md](docs/testing-fixtures.md). The
short version, which Claude must follow before touching any rule code:

1. Create `tests/fixtures/python/<RULE-ID>/` containing:
   - `fail_<description>.py` — code that MUST trigger the rule
   - `pass_<description>.py` — clean code that MUST NOT trigger the rule
   - `expected.json` — the rubric: severity, line, message substring per fixture
2. Run `pytest tests/test_fixture_corpus.py -k <RULE-ID>` and confirm the new
   cases **fail** (because the rule is not implemented yet).
3. Implement the rule.
4. Re-run; the cases must **pass**.
5. Run `gaudi-fixture-coverage` and confirm the rule shows `OK`.

The fixture is the specification. If you cannot write the broken code, you do
not understand the rule well enough to implement it. Boundary fixtures
(`fail_boundary_*.py` / `pass_boundary_*.py`) are required for any rule with
a numeric threshold.

CI runs `gaudi-fixture-coverage --strict`. Any rule without a complete
fixture directory fails CI — there is no warn-mode escape hatch.

## Known Issues (Alpha)

- Config system (`gaudi.toml`) loads but severity overrides not wired into engine. Glob-pattern exclusions ARE wired (see `[gaudi].exclude` in `gaudi.toml`).
- Some library rules use regex on raw text instead of AST (false positive risk)
- Test suite needs negative test cases (good code that shouldn't trigger)
