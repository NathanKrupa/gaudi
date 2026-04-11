# ABOUTME: Parametrized test runner for the per-rule fixture corpus.
# ABOUTME: Discovers tests/fixtures/<lang>/<RULE-ID>/ and asserts findings match expected.json.
from __future__ import annotations

import pytest

from gaudi.core import DEFAULT_SCHOOL, Finding
from gaudi.engine import Engine
from gaudi.packs.ops.pack import OpsPack
from gaudi.packs.ops.rules import ALL_RULES as OPS_RULES
from gaudi.packs.python.pack import PythonPack
from gaudi.packs.python.rules import ALL_RULES as PYTHON_RULES
from tests.fixture_corpus import (
    ExpectedFinding,
    FixtureCase,
    discover_all_cases,
    fixture_as_project,
)

_ALL_RULES_BY_CODE = {r.code: r for r in (*PYTHON_RULES, *OPS_RULES)}


def _school_for_rule(rule_id: str) -> str:
    """Pick a school that will run the rule under test.

    The fixture corpus is a per-rule specification: every fixture proves
    something about one rule, so the runner needs that rule to actually
    fire. Rules tagged with ``philosophy_scope`` limited to a subset of
    schools may not fire under the default school (``classical``), so we
    select a school the rule's scope accepts. Rules with the universal
    default (or a scope that includes ``classical``) fall back to the
    engine default.
    """
    rule = _ALL_RULES_BY_CODE.get(rule_id)
    if rule is None:
        return DEFAULT_SCHOOL
    scope = rule.philosophy_scope
    if "universal" in scope or DEFAULT_SCHOOL in scope:
        return DEFAULT_SCHOOL
    # Deterministic pick: the first school in sorted order.
    return sorted(scope)[0]


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
        school = _school_for_rule(case.rule_id)
        if school != DEFAULT_SCHOOL:
            # Write a gaudi.toml that selects a school under which the
            # rule under test actually runs. Directory fixtures may own
            # their own gaudi.toml; we only write one when the project
            # lacks it, so fixtures remain the source of truth for
            # project-shape tests.
            toml_path = project_root / "gaudi.toml"
            if not toml_path.exists():
                toml_path.write_text(f'[philosophy]\nschool = "{school}"\n', encoding="utf-8")
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
