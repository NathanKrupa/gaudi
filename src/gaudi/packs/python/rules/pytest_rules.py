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
    """Detect complex assertions without failure messages.

    Principles: #12 (Tests are the specification), #13 (The system must explain itself).
    Source: FWDOCS pytest assertion introspection — failure messages are the test's diagnostic surface.
    """

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
    """Detect expensive pytest fixtures without explicit scope.

    Principles: #12 (Tests are the specification).
    Source: FWDOCS pytest fixture optimization — expensive fixtures need wider scope.
    """

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


_OVERMOCK_THRESHOLD = 5
_FIXTURE_DEPENDENCY_THRESHOLD = 3
_TEST_BODY_LINE_LIMIT = 30


def _is_patch_decorator(dec: ast.expr) -> bool:
    """Return True if `dec` is a unittest.mock patch decorator (with or without args)."""
    target = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(target, ast.Name) and target.id == "patch":
        return True
    if isinstance(target, ast.Attribute) and target.attr == "patch":
        return True
    return False


class PytestOverMocking(Rule):
    """Detect tests smothered in @patch decorators.

    A test with five or more @patch decorators is testing the mocks, not the
    system under test.

    Principles: #12 (Tests are the specification).
    Source: ARCH90 anti-mock principle, FWDOCS pytest practice.
    """

    code = "TEST-ARCH-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    requires_library = "pytest"
    message_template = (
        "Over-mocked test '{name}' has {count} @patch decorators (threshold {threshold})"
    )
    recommendation_template = (
        "Five or more mocks usually means the test is exercising the mocks, not the code. "
        "Extract collaborators behind a seam, or write an integration test that uses real "
        "objects."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            if "test_" not in f.relative_path:
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not node.name.startswith("test_"):
                    continue
                patch_count = sum(1 for d in node.decorator_list if _is_patch_decorator(d))
                if patch_count >= _OVERMOCK_THRESHOLD:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            name=node.name,
                            count=patch_count,
                            threshold=_OVERMOCK_THRESHOLD,
                        )
                    )
        return findings


class PytestNoTestCoverage(Rule):
    """Detect src/<module>.py files with no matching tests/test_<module>.py.

    A source module with no test file is a coverage gap that even line-coverage
    tools cannot report on, because they only see modules the test suite imports.

    Principles: #12 (Tests are the specification).
    Source: pytest convention `tests/test_<module>.py`; ARCH90 testing curriculum.
    """

    code = "TEST-ARCH-002"
    severity = Severity.INFO
    category = Category.STRUCTURE
    requires_library = "pytest"
    message_template = "Source module '{file}' has no matching test file under tests/"
    recommendation_template = (
        "Add tests/test_{stem}.py (or tests/<subpath>/test_{stem}.py) so this module has a "
        "direct test surface. Some modules legitimately have no tests -- if so, suppress "
        "this rule for the file."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        src_files = [
            f
            for f in context.files
            if f.relative_path.replace("\\", "/").startswith("src/")
            and not f.path.name.startswith("__")
        ]
        if not src_files:
            return findings
        test_stems = {
            f.path.stem
            for f in context.files
            if "tests" in f.relative_path.replace("\\", "/").split("/")
            and f.path.name.startswith("test_")
        }
        for f in src_files:
            stem = f.path.stem
            expected_test = f"test_{stem}"
            if expected_test not in test_stems:
                findings.append(
                    self.finding(file=f.relative_path, stem=stem)
                )
        return findings


class PytestAssertInProductionCode(Rule):
    """Detect `assert` statements used as runtime validation in non-test code.

    `assert` is stripped under `python -O`, so any production assert is
    silently disabled in optimized runs. Use explicit exceptions for
    validation.

    Principles: #4 (Failure must be named).
    Source: PEP 8, Python language reference on the `assert` statement.
    """

    code = "TEST-ARCH-003"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = "Production code uses assert at line {line} -- stripped under python -O"
    recommendation_template = (
        "Replace `assert <cond>` with `if not <cond>: raise ValueError(...)` (or another "
        "explicit exception). Asserts are for tests and internal debug-mode invariants, not "
        "for input validation."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            rel = f.relative_path.replace("\\", "/")
            if "test" in rel or "conftest" in rel:
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


class PytestFixtureDependencyDepth(Rule):
    """Detect pytest fixtures that depend on three or more other fixtures.

    A fixture that pulls in many other fixtures hides its setup behind layers
    of indirection, making test failures hard to trace.

    Principles: #11 (The reader is the user).
    Source: pytest fixture composition guidance; FWDOCS pytest practice.
    """

    code = "TEST-STRUCT-002"
    severity = Severity.INFO
    category = Category.STRUCTURE
    requires_library = "pytest"
    message_template = (
        "Fixture '{name}' depends on {count} other fixtures (threshold {threshold})"
    )
    recommendation_template = (
        "Flatten the fixture graph: inline trivial dependencies, or compose explicit setup "
        "objects in a single fixture. Deep fixture chains make failure diagnosis painful."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            rel = f.relative_path.replace("\\", "/")
            if "conftest" not in rel and "test_" not in rel:
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not self._is_pytest_fixture(node):
                    continue
                deps = [
                    a.arg for a in node.args.args if a.arg not in {"self", "cls", "request"}
                ]
                if len(deps) >= _FIXTURE_DEPENDENCY_THRESHOLD:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            name=node.name,
                            count=len(deps),
                            threshold=_FIXTURE_DEPENDENCY_THRESHOLD,
                        )
                    )
        return findings

    @staticmethod
    def _is_pytest_fixture(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        for dec in func.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if isinstance(target, ast.Attribute) and target.attr == "fixture":
                if isinstance(target.value, ast.Name) and target.value.id == "pytest":
                    return True
            if isinstance(target, ast.Name) and target.id == "fixture":
                return True
        return False


class PytestTestMethodTooLong(Rule):
    """Detect test functions whose body exceeds 30 lines.

    Arrange/act/assert should be short enough to read at a glance. Long tests
    usually mean too many behaviours under one name.

    Principles: #11 (The reader is the user), #12 (Tests are the specification).
    Source: Beck *Test-Driven Development*; pytest best practices.
    """

    code = "TEST-STRUCT-003"
    severity = Severity.WARN
    category = Category.STRUCTURE
    requires_library = "pytest"
    message_template = (
        "Test '{name}' body is {length} lines (limit {limit}) -- split it"
    )
    recommendation_template = (
        "A test should exercise one behaviour. Split the function along its arrange/act/"
        "assert seams, or extract setup into a fixture."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            if "test_" not in f.relative_path:
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not node.name.startswith("test_"):
                    continue
                length = self._body_length(node)
                if length > _TEST_BODY_LINE_LIMIT:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            name=node.name,
                            length=length,
                            limit=_TEST_BODY_LINE_LIMIT,
                        )
                    )
        return findings

    @staticmethod
    def _body_length(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        if not func.body:
            return 0
        first = func.body[0].lineno
        last = func.body[-1].end_lineno or func.body[-1].lineno
        return last - first + 1


PYTEST_RULES = (
    PytestAssertMessage(),
    PytestFixtureScope(),
    PytestOverMocking(),
    PytestNoTestCoverage(),
    PytestAssertInProductionCode(),
    PytestFixtureDependencyDepth(),
    PytestTestMethodTooLong(),
)
