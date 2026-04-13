# Gaudi

**Not just structurally sound. Beautiful.**

Gaudi is an architecture linter for Python projects. It inspects your project's structural design and produces machine-readable error codes that AI coding agents (Claude, Copilot, etc.) can understand and act on.

Style linters catch syntax. Security scanners catch vulnerabilities. **Gaudi catches architecture mistakes** — the kind that cost you six months of refactoring when you hit 10,000 users.

## What It Does

```bash
$ gaudi check .

ARCH-001 [ERROR] models.py:14 - Multi-tenant table 'donors' has no tenant isolation column
  -> Add a `tenant_id` ForeignKey and enforce row-level filtering on all queries.

IDX-001 [WARN] models.py:28 - Column 'email' is used in filter queries but has no db_index
  -> Add db_index=True or create a composite index.

SCHEMA-001 [INFO] models.py:45 - Model 'Donor' has no timestamp fields (created_at, updated_at)
  -> Add created_at and updated_at DateTimeField columns for debugging and auditing.

Found 1 error, 1 warning, 1 info across 3 files.
```

## Why Gaudi Exists

AI coding agents are writing more and more of our code. They're great at implementing features. They're terrible at asking, *"Should this be built this way?"*

Gaudi is the discipline layer. It encodes architectural best practices into structured error codes that any AI agent can parse, understand, and resolve — without ambiguity, without hallucination.

**For humans:** Catch design mistakes before they become technical debt.
**For AI agents:** Get structured, actionable architecture guidance instead of vague "best practices" prompts.

## Installation

```bash
pip install gaudi-linter
```

## Quick Start

```bash
# Check a project directory
gaudi check .

# Output as JSON (for AI agent consumption)
gaudi check . --format json

# Output as GitHub Actions annotations (inline on PRs)
gaudi check . --format github

# Only errors
gaudi check . --severity error --exit-code

# Check a specific file
gaudi check models.py

# Generate a Markdown report you can paste into a chat with an LLM
gaudi report . --output gaudi-report.md
```

## LLM-collaborative workflow

Gaudi is designed to be the opening move in a developer ↔ LLM conversation,
not a list of mechanical autofixes. Most rules are judgment calls — the
*right* thing to do about a finding depends on the surrounding code and the
project's priorities.

Two outputs make that conversation cheap to start:

- **`gaudi check --format github`** emits
  [GitHub Actions workflow commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-error-message)
  so findings render inline on pull requests, in the Files Changed view, exactly
  where reviewers (and Copilot/Claude PR reviewers) expect them. See
  [docs/llm-workflow.md](docs/llm-workflow.md) for a sample workflow.
- **`gaudi report .`** writes a Markdown report grouped by file. Each finding
  includes a code snippet, the rule's recommendation, and a pre-written
  "Discuss with LLM" prompt the developer can paste straight into Claude,
  ChatGPT, or any other assistant.

## What It Checks

Gaudi uses deep AST analysis to inspect Django models, SQLAlchemy tables, FastAPI endpoints, Flask apps, Celery tasks, Pandas operations, Pydantic models, pytest fixtures, and DRF views.

### Rule Categories

| Prefix | Category | Examples |
|--------|----------|----------|
| `ARCH` | Architecture | Tenant isolation, god models, nullable FK sprawl |
| `IDX` | Indexing | Missing indexes on lookup/filter fields |
| `SCHEMA` | Schema Design | Missing timestamps, column sprawl, type choices |
| `SEC` | Security | Hardcoded secrets, missing permissions, unsafe defaults |
| `SCALE` | Scalability | N+1 queries, missing timeouts, iterrows() |
| `STRUCT` | Structure | Fat files, missing app factories |

### Library-Specific Rules

| Prefix | Library | Rules |
|--------|---------|-------|
| `DJ` | Django | Secret key exposure, DEBUG=True, fat views |
| `FAPI` | FastAPI | Missing response_model, sync endpoints |
| `SA` | SQLAlchemy | Session leaks, default lazy loading |
| `FLASK` | Flask | Module-level app creation |
| `CELERY` | Celery | Missing retries, missing time limits |
| `PD` | Pandas | inplace=True, iterrows() |
| `HTTP` | Requests/HTTPX | Missing timeouts, no retry logic |
| `PYD` | Pydantic | Mutable default values |
| `TEST` | pytest | Complex assertions, expensive fixtures |
| `DRF` | Django REST Framework | Missing permissions, no throttling |
| `PY314` | Python 3.14 | Removed APIs, deprecated modules |

## Error Code Format

Every finding follows a consistent schema:

```json
{
  "code": "ARCH-001",
  "severity": "error",
  "category": "architecture",
  "file": "models.py",
  "line": 14,
  "message": "Multi-tenant table 'donors' has no tenant isolation column",
  "recommendation": "Add a `tenant_id` ForeignKey and enforce row-level filtering."
}
```

## Writing Custom Rules

```python
from gaudi import Rule, Severity, Category

class CheckTenantIsolation(Rule):
    code = "ARCH-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "Multi-tenant table '{table}' has no tenant isolation column"

    def check(self, context):
        for model in context.models:
            if not model.has_column("tenant_id"):
                yield self.finding(
                    file=model.source_file,
                    line=model.source_line,
                    table=model.name,
                )
```

## AI Agent Integration

Gaudi's JSON output is designed to be consumed by AI coding agents. Add it to your Claude Code workflow, your CI pipeline, or your custom agent loop.

```bash
# Use in CI
gaudi check . --format json --severity error --exit-code

# Use in a pre-commit hook
gaudi check . --severity error --exit-code
```

### Prompt Fragment for AI Agents

Include this in your system prompt or project instructions:

```
Before implementing any database schema changes, run `gaudi check .` and resolve
all ERROR-level findings. WARN-level findings should be addressed unless you can
document a specific reason to override them.
```

## Configuration

Create a `gaudi.toml` in your project root:

```toml
[gaudi]
severity = "warn"          # minimum severity to report
exclude = ["migrations/"]  # paths to skip

[gaudi.rules]
"ARCH-001" = "error"       # override severity
"IDX-003" = "off"          # disable a rule entirely

[philosophy]
school = "convention"      # infer with: gaudi philosophy .
```

### Inline suppression

Suppress findings on a single line with `# noqa`:

```python
SECRET_KEY = "test-only"  # noqa: DJ-SEC-001
urlpatterns = [...]       # noqa
```

`# noqa` (bare) suppresses all findings on that line. `# noqa: CODE1, CODE2` suppresses only the listed rules.

### Rule cheat-sheet

Generate a one-line-per-rule markdown file from the live registry, suitable
for `@`-reference from `CLAUDE.md` or any other AI agent instructions file:

```bash
# Print to stdout
gaudi cheat-sheet

# Write to a file (committed artifact)
gaudi cheat-sheet -o docs/gaudi-rules.md

# CI drift guard: exit 1 if the file is out of date
gaudi cheat-sheet --check -o docs/gaudi-rules.md
```

The committed artifact at [`docs/gaudi-rules.md`](docs/gaudi-rules.md) is
generated from rule `recommendation_template` fields. It cannot drift.

### Philosophy inference

Gaudi can recommend which architectural school best matches your project:

```bash
gaudi philosophy .
```

This analyzes your dependencies and project structure to suggest a school (e.g., `convention` for Django projects, `data-oriented` for NumPy pipelines).

## Known Limitations (v0.1 alpha)

- Some library-specific rules use regex on raw text instead of full AST analysis, which can produce false positives.

These are tracked in the [issue tracker](https://github.com/NathanKrupa/gaudi/issues).

## Philosophy

Gaudi is named after Antoni Gaudi, the architect of La Sagrada Familia. He built hanging chain models — inverted catenary arches — to test structural integrity *before* laying a single stone. Construction on his masterwork began in 1882 and continues today, still following his structural principles.

This tool embodies that philosophy: **validate the architecture before you build.** The earlier you catch a structural flaw, the less it costs to fix. And with AI agents writing increasingly large portions of our codebases, we need automated architectural discipline more than ever.

The first principles that govern Gaudi — fourteen numbered claims in three pillars (Truthfulness, Economy, Cost-honesty) — are written down in [docs/principles.md](https://github.com/NathanKrupa/gaudi/blob/main/docs/principles.md). They are intended to be portable: any project can adopt them as the doctrine its design decisions appeal to.

## Contributing

Contributions welcome. The highest-impact contributions right now:

1. **New rules** — especially Django, FastAPI, and SQLAlchemy patterns
2. **Code smell detection** — implementing Fowler's 24 code smells programmatically
3. **CI/CD integration examples** — GitHub Actions, GitLab CI, etc.

See [CONTRIBUTING.md](https://github.com/NathanKrupa/gaudi/blob/main/CONTRIBUTING.md) for details.

## License

MIT License. See [LICENSE](https://github.com/NathanKrupa/gaudi/blob/main/LICENSE) for details.

---

*Built by [Nathan Krupa](https://thealmoner.com) — fundraiser, writer, and reluctant architect.*
