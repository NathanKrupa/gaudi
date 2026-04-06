# Contributing to Gaudí

Thanks for your interest in contributing! Gaudí is a young project and contributions of all kinds are welcome.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/gaudi.git`
3. Install in development mode: `pip install -e ".[dev]"`
4. Run the tests: `pytest`
5. Create a branch for your work: `git checkout -b my-feature`

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
- Run `ruff check .` and `ruff format .` before committing
- Type hints are required for all public APIs
- Every rule must have a docstring explaining what it catches and why

## Testing

- All rules must have test coverage
- Use fixture files in `tests/fixtures/` for test data
- Run the full suite with `pytest -v`

## Pull Request Process

1. Ensure all tests pass
2. Update the README if you've added rules or packs
3. Add yourself to CONTRIBUTORS.md if you'd like
4. Submit a PR with a clear description of what you've added and why

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
