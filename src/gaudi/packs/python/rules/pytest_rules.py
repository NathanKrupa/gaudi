# ABOUTME: Pytest-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers assertion messages and fixture scope optimization.
from __future__ import annotations

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class PytestAssertMessage(Rule):
    code = "TEST-STRUCT-001"
    severity = Severity.INFO
    category = Category.STRUCTURE
    message_template = "Complex assertion without message at line {line}"
    recommendation_template = (
        "Add a failure message to complex assertions: assert condition, 'description'. "
        "Messages make test failures easier to diagnose."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "test_" not in f.relative_path:
                continue
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("assert ") and "," not in stripped and len(stripped) > 40:
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class PytestFixtureScope(Rule):
    code = "TEST-SCALE-001"
    severity = Severity.INFO
    category = Category.SCALABILITY
    message_template = "Expensive fixture without scope at line {line}"
    recommendation_template = (
        "Add scope='session' or scope='module' to fixtures that create expensive resources "
        "(database connections, API clients) to avoid recreating them per test."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        expensive_patterns = [
            "connection",
            "engine",
            "client",
            "session",
            "database",
            "db",
        ]
        for f in context.files:
            if "conftest" not in f.relative_path:
                continue
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "@pytest.fixture" in line and "scope=" not in line:
                    # Check fixture name
                    next_lines = source.splitlines()[i : i + 3]
                    func_line = "\n".join(next_lines)
                    if any(p in func_line.lower() for p in expensive_patterns):
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


PYTEST_RULES = [PytestAssertMessage(), PytestFixtureScope()]
