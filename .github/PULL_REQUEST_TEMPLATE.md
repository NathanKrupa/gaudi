## Summary

<!-- What does this PR do? Keep it to 1-3 bullet points. -->

## Motivation

<!-- Why is this change needed? Link to issue if applicable. -->

## Review checklist

- [ ] Tests pass (`pytest --tb=short`)
- [ ] Linting passes (`ruff check . && ruff format --check .`)
- [ ] Any new or changed rule has a fixture directory under `tests/fixtures/python/<RULE-ID>/` with at least one `fail_*.py`, one `pass_*.py`, and an `expected.json` (see [docs/testing-fixtures.md](../docs/testing-fixtures.md))
- [ ] No new dependencies added without discussion
- [ ] No changes to CI/CD workflows, build config, or packaging without maintainer approval
- [ ] No hardcoded secrets, tokens, or credentials
- [ ] No obfuscated code (base64 strings, hex payloads, minified blobs)
- [ ] No `eval()`, `exec()`, `subprocess.call(shell=True)`, or similar dangerous patterns
- [ ] Changes match the PR description (no unrelated modifications)

## Security considerations

<!-- If this PR touches dependencies, CI, packaging, or entry points, explain why. -->
<!-- Delete this section if not applicable. -->

## Test plan

<!-- How did you verify this works? -->
