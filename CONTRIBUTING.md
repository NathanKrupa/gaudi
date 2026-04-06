# Contributing to Gaudí

Thanks for your interest in contributing! Gaudí is a young project and contributions of all kinds are welcome.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/gaudi.git`
3. Install in development mode: `pip install -e ".[dev]"`
4. Install pre-commit hooks: `pre-commit install`
5. Run the tests: `pytest`
6. Create a branch for your work: `git checkout -b my-feature`

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
- A class in `src/gaudi/packs/python/rules.py`
- A unique error code following the prefix conventions
- A clear `message_template` and `recommendation_template`
- A test case with a fixture that triggers it

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
- Use fixture files in `tests/fixtures/` for test data
- Run the full suite with `pytest`
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
