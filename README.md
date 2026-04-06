# Gaudí

**Not just structurally sound. Beautiful.**

Gaudí is a universal architecture linter that inspects your project's structural design and produces machine-readable error codes that AI coding agents (Claude, Copilot, etc.) can understand and act on.

Style linters catch syntax. Security scanners catch vulnerabilities. **Gaudí catches architecture mistakes** — the kind that cost you six months of refactoring when you hit 10,000 users.

## What It Does

```bash
$ gaudi check .

ARCH-001 [ERROR] models.py:14 - Multi-tenant table 'donors' has no tenant isolation column
  → Add a `tenant_id` ForeignKey and enforce row-level filtering on all queries.

IDX-001 [WARN] models.py:28 - Column 'email' is used in filter queries but has no db_index
  → Add db_index=True or create a composite index.

REL-002 [INFO] models.py:45 - Nullable ForeignKey 'organization' may indicate optional relationship that should be a separate table
  → Consider whether this represents a true optional relationship or a missing join table.

Found 1 error, 1 warning, 1 info across 3 files.
```

## Why Gaudí Exists

AI coding agents are writing more and more of our code. They're great at implementing features. They're terrible at asking, *"Should this be built this way?"*

Gaudí is the discipline layer. It encodes architectural best practices into structured error codes that any AI agent can parse, understand, and resolve — without ambiguity, without hallucination.

**For humans:** Catch design mistakes before they become technical debt.
**For AI agents:** Get structured, actionable architecture guidance instead of vague "best practices" prompts.

## Installation

```bash
NOT READY FOR PRIME TIME YET
```

## Quick Start

```bash
# Check a project directory
gaudi check .

# Check with a specific language pack
gaudi check . --pack python

# Output as JSON (for AI agent consumption)
gaudi check . --format json

# Check a specific file
gaudi check models.py
```

## Language Packs

Gaudí is language-agnostic at its core. Language packs teach it the architectural patterns and anti-patterns for specific stacks.

| Pack | Status | Covers |
|------|--------|--------|
| `python` | ✅ v0.1 | Django models, SQLAlchemy, FastAPI, general Python project structure |
| `javascript` | 🔜 Planned | Prisma, Express, Next.js, general Node project structure |
| `go` | 🔜 Planned | Interface design, error handling, package structure |
| `rust` | 🔜 Planned | Module organization, trait design, error types |

## Error Code Format

Every Gaudí finding follows a consistent schema:

```json
{
  "code": "ARCH-001",
  "severity": "error",
  "category": "architecture",
  "file": "models.py",
  "line": 14,
  "message": "Multi-tenant table 'donors' has no tenant isolation column",
  "recommendation": "Add a `tenant_id` ForeignKey and enforce row-level filtering on all queries.",
  "context": {
    "table_name": "donors",
    "pattern": "multi-tenant-isolation"
  }
}
```

### Error Code Prefixes

| Prefix | Category | Examples |
|--------|----------|----------|
| `ARCH` | Architecture | Tenant isolation, separation of concerns, layering violations |
| `IDX` | Indexing | Missing indexes, redundant indexes, index strategy |
| `REL` | Relationships | Foreign key design, join tables, circular references |
| `SCHEMA` | Schema Design | Column sprawl, naming conventions, type choices |
| `SEC` | Security | Exposed secrets, missing auth boundaries, unsafe defaults |
| `SCALE` | Scalability | N+1 query patterns, unbounded queries, missing pagination |
| `STRUCT` | Project Structure | File organization, module boundaries, dependency direction |

## Writing Custom Rules

```python
from gaudi import Rule, Severity

class CheckTenantIsolation(Rule):
    code = "ARCH-001"
    severity = Severity.ERROR
    category = "architecture"
    message = "Multi-tenant table '{table}' has no tenant isolation column"

    def check(self, context):
        for table in context.tables:
            if table.is_multi_tenant and not table.has_column("tenant_id"):
                yield self.finding(
                    file=table.source_file,
                    line=table.source_line,
                    table=table.name,
                    recommendation=f"Add a `tenant_id` column to `{table.name}` and enforce row-level filtering."
                )
```

## AI Agent Integration

Gaudí's JSON output is designed to be consumed by AI coding agents. Add it to your Claude Code workflow, your CI pipeline, or your custom agent loop.

```bash
# Pipe findings to Claude Code
gaudi check . --format json | claude-code fix

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
packs = ["python"]
severity = "warn"          # minimum severity to report
exclude = ["migrations/"]  # paths to skip

[gaudi.rules]
"ARCH-001" = "error"       # override severity
"IDX-003" = "off"          # disable specific rule

[gaudi.python]
framework = "django"       # framework-specific checks
```

## Philosophy

Gaudí is named after Antoni Gaudí, the architect of La Sagrada Família. He built hanging chain models — inverted catenary arches — to test structural integrity *before* laying a single stone. Construction on his masterwork began in 1882 and continues today, still following his structural principles.

This tool embodies that philosophy: **validate the architecture before you build.** The earlier you catch a structural flaw, the less it costs to fix. And with AI agents writing increasingly large portions of our codebases, we need automated architectural discipline more than ever.

## Contributing

Contributions welcome. The highest-impact contributions right now:

1. **New rules for the Python pack** — especially Django and FastAPI patterns
2. **New language packs** — JavaScript/TypeScript is the most requested
3. **CI/CD integration examples** — GitHub Actions, GitLab CI, etc.
4. **Documentation** — usage guides, rule explanations, architectural pattern guides

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT License. See [LICENSE](LICENSE) for details.

---

*Built by [Nathan Krupa](https://thealmoner.com) — fundraiser, writer, and reluctant architect.*
