# ABOUTME: Parametrized test runner for the per-rule fixture corpus.
# ABOUTME: Discovers tests/fixtures/<lang>/<RULE-ID>/ and asserts findings match expected.json.
from __future__ import annotations

import pytest

from gaudi.core import Finding
from gaudi.engine import Engine
from gaudi.packs.ops.pack import OpsPack
from gaudi.packs.python.pack import PythonPack
from tests.fixture_corpus import (
    ExpectedFinding,
    FixtureCase,
    discover_all_cases,
    fixture_as_project,
)

_CASES = discover_all_cases()
_MISMATCH = "{test_id}: {field} mismatch -- expected {expected}, got {actual}"


def _make_engine() -> Engine:
    """Engine wired with every pack a fixture might need.

    The corpus runner registers packs explicitly rather than relying on
    entry-point discovery, so the test suite is hermetic and does not depend
    on the active install state of gaudi-linter.
    """
    engine = Engine()
    engine.register_pack(PythonPack())
    engine.register_pack(OpsPack())
    return engine


def _assert_finding_matches(finding: Finding, expectation: ExpectedFinding, test_id: str) -> None:
    assert finding.severity.value == expectation.severity, _MISMATCH.format(
        test_id=test_id,
        field="severity",
        expected=expectation.severity,
        actual=finding.severity.value,
    )
    assert expectation.message_contains in finding.message, (
        f"{test_id}: message {finding.message!r} does not contain {expectation.message_contains!r}"
    )
    if expectation.line is not None:
        assert finding.line == expectation.line, _MISMATCH.format(
            test_id=test_id, field="line", expected=expectation.line, actual=finding.line
        )


@pytest.mark.skipif(not _CASES, reason="No fixture cases discovered")
@pytest.mark.parametrize("case", _CASES, ids=lambda c: c.test_id)
def test_fixture_case(case: FixtureCase) -> None:
    """Run the Python pack against one fixture file and assert its expected findings.

    The runner filters findings to only those matching the rule under test, so a
    fixture incidentally tripping unrelated rules won't fail this assertion. The
    fixture corpus rubric is: each fixture proves something about *one* rule.
    """
    engine = _make_engine()
    with fixture_as_project(case) as project_root:
        all_findings = engine.check(project_root)
    findings = [f for f in all_findings if f.code == case.rule_id]

    assert len(findings) == len(case.expected), (
        f"{case.test_id}: expected {len(case.expected)} finding(s) for {case.rule_id}, "
        f"got {len(findings)}: {[f.message for f in findings]}"
    )

    sorted_findings = sorted(findings, key=lambda f: (f.line or 0, f.message))
    sorted_expected = sorted(case.expected, key=lambda e: (e.line or 0, e.message_contains))
    for finding, expectation in zip(sorted_findings, sorted_expected):
        _assert_finding_matches(finding, expectation, case.test_id)
