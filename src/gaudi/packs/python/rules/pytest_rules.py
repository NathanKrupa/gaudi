# ABOUTME: Pytest-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers assertion messages and fixture scope optimization via AST.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext

_EXPENSIVE_FIXTURE_NAMES = frozenset(
    {"connection", "engine", "client", "session", "database", "db"}
)


class PytestAssertMessage(Rule):
    code = "TEST-STRUCT-001"
    severity = Severity.INFO
    category = Category.STRUCTURE
    requires_library = "pytest"
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
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assert):
                    continue
                # No failure message provided
                if node.msg is not None:
                    continue
                # Only flag complex assertions (BoolOp, Compare chains)
                test = node.test
                is_complex = (
                    isinstance(test, ast.BoolOp)
                    or (isinstance(test, ast.Compare) and len(test.comparators) > 1)
                    or (isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not))
                )
                if is_complex:
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


class PytestFixtureScope(Rule):
    code = "TEST-SCALE-001"
    severity = Severity.INFO
    category = Category.SCALABILITY
    requires_library = "pytest"
    message_template = "Expensive fixture without scope at line {line}"
    recommendation_template = (
        "Add scope='session' or scope='module' to fixtures that create expensive resources "
        "(database connections, API clients) to avoid recreating them per test."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "conftest" not in f.relative_path:
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                if not self._has_fixture_without_scope(node):
                    continue
                # Check if fixture name suggests expensive resource
                if any(p in node.name.lower() for p in _EXPENSIVE_FIXTURE_NAMES):
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings

    @staticmethod
    def _has_fixture_without_scope(func: ast.FunctionDef) -> bool:
        """Check if function has @pytest.fixture without scope= kwarg."""
        for dec in func.decorator_list:
            # @pytest.fixture (no args)
            if (
                isinstance(dec, ast.Attribute)
                and dec.attr == "fixture"
                and isinstance(dec.value, ast.Name)
                and dec.value.id == "pytest"
            ):
                return True
            # @pytest.fixture() (with args but no scope)
            if isinstance(dec, ast.Call):
                func_node = dec.func
                if (
                    isinstance(func_node, ast.Attribute)
                    and func_node.attr == "fixture"
                    and isinstance(func_node.value, ast.Name)
                    and func_node.value.id == "pytest"
                ):
                    if not any(kw.arg == "scope" for kw in dec.keywords):
                        return True
        return False


PYTEST_RULES = (PytestAssertMessage(), PytestFixtureScope())
