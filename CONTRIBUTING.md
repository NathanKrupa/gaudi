# Contributing to Gaudí

Thanks for your interest in contributing! Gaudí is a young project and contributions of all kinds are welcome.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/gaudi.git`
3. Create a venv: `python -m venv .venv`
4. Activate it: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix)
5. Install in development mode: `pip install -e ".[dev]"`
6. Install pre-commit hooks: `pre-commit install`
7. Run the tests: `pytest`
8. Create a branch for your work: `git checkout -b my-feature`

## Security Policy

We take supply chain security seriously. All contributions are reviewed with this in mind.

### What gets extra scrutiny

- **CI/CD changes** (`.github/workflows/`, pre-commit config): Require maintainer approval. These run with elevated trust.
- **Dependency changes** (`pyproject.toml`, `requirements-lock.txt`): New dependencies must be discussed in an issue first. We prefer writing 20 lines of code over adding a package.
- **Build/packaging changes** (`pyproject.toml` entry points, `setup.cfg`): Require maintainer approval.
- **Obfuscated content**: Base64 strings, hex-encoded payloads, minified blobs, or large binary fixtures will be rejected.

### What will be rejected outright

- `eval()`, `exec()`, or `subprocess.call(shell=True)` without clear justification
- Hardcoded secrets, tokens, or credentials
- Test fixtures containing executable content beyond what the test requires
- PRs where the diff doesn't match the description

### Signed commits

We recommend (but don't yet require) [signed commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits). This may become mandatory as the project matures.

## Editorial Doctrine

Every rule design question in Gaudi must appeal to a principle. The fourteen
numbered principles in three pillars (Truthfulness, Economy, Cost-honesty)
govern which rules enter the catalog, how thresholds and severities are
assigned, and when a rule should be cut. Read
[docs/principles.md](docs/principles.md) before proposing a new rule or
changing a threshold.

## High-Impact Contributions

These are the areas where contributions will have the most impact right now:

### New Rules for the Python Pack

The Python pack ships with 10 rules. There are dozens more worth adding. Good candidates:

- N+1 query detection patterns (SCALE-001)
- Circular foreign key detection (REL-001)
- Missing `__str__` on Django models (SCHEMA-004)
- Raw SQL usage without parameterization (SEC-002)
- Unbounded queryset in views (SCALE-002)
- Missing migration files (STRUCT-002)

Each rule needs:
- A class in the appropriate `src/gaudi/packs/python/rules/<category>.py` module
- A unique error code following the prefix conventions
- A clear `message_template` and `recommendation_template`
- A **fixture corpus directory** under `tests/fixtures/python/<RULE-ID>/` containing
  at least one `fail_*.py`, one `pass_*.py`, and an `expected.json`. The
  parametrized runner in `tests/test_fixture_corpus.py` will pick these up
  automatically. Boundary fixtures (`fail_boundary_*.py` / `pass_boundary_*.py`)
  are strongly encouraged for any rule with a numeric threshold.

### Fixture-first TDD

The fixture is the specification; the rule is the implementation. The workflow
is mandatory for every new rule:

1. Create the rule directory and write `fail_*.py`, `pass_*.py`, and `expected.json`.
2. Run `pytest tests/test_fixture_corpus.py` and confirm the new cases **fail**
   (the rule does not exist yet).
3. Implement the rule.
4. Re-run the suite and confirm the cases now **pass**.
5. Verify with `gaudi-fixture-coverage` that the new rule shows `OK` in the
   coverage table.

The full rubric, naming conventions, and expected.json schema live in
[docs/testing-fixtures.md](docs/testing-fixtures.md).

### New Language Packs

Every language has architectural pitfalls. To create a new pack:

1. Create `src/gaudi/packs/LANGUAGE/`
2. Implement `context.py` (what gets parsed), `parser.py` (how to parse it), `rules.py` (what to check), and `pack.py` (wiring)
3. Register the pack in `pyproject.toml` under `[project.entry-points."gaudi.packs"]`
4. Add tests in `tests/`

### CI/CD Integration Examples

Show people how to use Gaudí in their pipelines:
- GitHub Actions workflow
- GitLab CI config
- Pre-commit hook configuration

## Code Style

- We use `ruff` for formatting and linting
- Run `ruff check .` and `ruff format .` before committing (or just use the pre-commit hooks)
- Type hints are required for all public APIs
- Every rule must have a docstring explaining what it catches and why

## Testing

- All rules must have test coverage
- New rules use the per-rule fixture corpus under `tests/fixtures/python/<RULE-ID>/`
  with an `expected.json` rubric (see [docs/testing-fixtures.md](docs/testing-fixtures.md))
- Run the full suite with `pytest`
- Run `gaudi-fixture-coverage --strict` — every rule must have a complete
  fixture directory; CI enforces this
- CI enforces a minimum coverage threshold

## Pull Request Process

1. **Keep PRs focused.** One feature or fix per PR. Large PRs that bundle unrelated changes will be asked to split.
2. Ensure all tests pass and pre-commit hooks are clean
3. Fill out the PR template completely, including the security checklist
4. Update the README if you've added rules or packs
5. Add yourself to CONTRIBUTORS.md if you'd like
6. PRs require at least one maintainer review before merge

### First-time contributors

Welcome! Your first PR will require maintainer approval before CI runs (GitHub's default for fork PRs). This is a security measure, not a trust issue. We review promptly.

## Commit access

Write access to the repository is granted conservatively and reviewed periodically. Consistent, high-quality contributions over time are the path to commit access. This protects everyone, including you.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
