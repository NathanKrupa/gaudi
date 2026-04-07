# ABOUTME: Parametrized test runner for the per-rule fixture corpus.
# ABOUTME: Discovers tests/fixtures/python/<RULE-ID>/ and asserts findings match expected.json.
from __future__ import annotations

import pytest

from gaudi.packs.python.pack import PythonPack
from tests.fixture_corpus import FixtureCase, discover_cases, fixture_as_project

_CASES = discover_cases("python")


@pytest.mark.skipif(not _CASES, reason="No fixture cases discovered")
@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.test_id)
def test_fixture_case(case: FixtureCase) -> None:
    """Run the Python pack against one fixture file and assert its expected findings.

    The runner filters findings to only those matching the rule under test, so a
    fixture incidentally tripping unrelated rules won't fail this assertion. The
    fixture corpus rubric is: each fixture proves something about *one* rule.
    """
    pack = PythonPack()
    with fixture_as_project(case) as project_root:
        all_findings = pack.check(project_root)

    findings = [f for f in all_findings if f.code == case.rule_id]

    assert len(findings) == len(case.expected), (
        f"{case.test_id}: expected {len(case.expected)} finding(s) for {case.rule_id}, "
        f"got {len(findings)}: {[f.message for f in findings]}"
    )

    # Match expectations to findings positionally after sorting both by line.
    sorted_findings = sorted(findings, key=lambda f: (f.line or 0, f.message))
    sorted_expected = sorted(case.expected, key=lambda e: (e.line or 0, e.message_contains))

    for finding, expectation in zip(sorted_findings, sorted_expected):
        assert finding.severity.value == expectation.severity, (
            f"{case.test_id}: severity mismatch -- "
            f"expected {expectation.severity}, got {finding.severity.value}"
        )
        assert expectation.message_contains in finding.message, (
            f"{case.test_id}: message {finding.message!r} does not contain "
            f"{expectation.message_contains!r}"
        )
        if expectation.line is not None:
            assert finding.line == expectation.line, (
                f"{case.test_id}: line mismatch -- expected {expectation.line}, got {finding.line}"
            )
