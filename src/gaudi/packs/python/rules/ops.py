# ABOUTME: Operational scaffolding rules for project governance files.
# ABOUTME: Checks for pre-commit config, PR template, CODEOWNERS, and contributing guide.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# OPS-002  MissingPrecommit
# ---------------------------------------------------------------


class MissingPrecommit(Rule):
    """Detect projects without a pre-commit configuration.

    Principles: #12 (Tests are the specification).
    Source: ARCH90 Day 6 — pre-commit hooks gate the build before CI does.
    """

    code = "OPS-002"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no .pre-commit-config.yaml"
    recommendation_template = (
        "Add pre-commit hooks for automated code quality checks before each commit."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        path = context.root / ".pre-commit-config.yaml"
        if not path.exists():
            return [self.finding()]
        return []


# ---------------------------------------------------------------
# OPS-003  MissingPRTemplate
# ---------------------------------------------------------------


class MissingPRTemplate(Rule):
    """Detect projects without a pull request template.

    Principles: #8 (Smallest reasonable change).
    Source: ARCH90 — PRs are the project's task board.
    """

    code = "OPS-003"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no pull request template"
    recommendation_template = (
        "Add .github/PULL_REQUEST_TEMPLATE.md to enforce"
        " consistent PR descriptions with summary, motivation,"
        " and test plan sections."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        paths = [
            context.root / ".github" / "PULL_REQUEST_TEMPLATE.md",
            context.root / ".github" / "pull_request_template.md",
            context.root / "PULL_REQUEST_TEMPLATE.md",
        ]
        if any(p.exists() for p in paths):
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# OPS-004  MissingCodeowners
# ---------------------------------------------------------------


class MissingCodeowners(Rule):
    """Detect projects without a CODEOWNERS file.

    Principles: #11 (The reader is the user).
    Source: ARCH90 — CODEOWNERS routes review to the right reader.
    """

    code = "OPS-004"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no CODEOWNERS file"
    recommendation_template = (
        "Add .github/CODEOWNERS to assign review responsibility."
        " Without it, PRs have no automatic reviewer assignment."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        paths = [
            context.root / ".github" / "CODEOWNERS",
            context.root / "CODEOWNERS",
        ]
        if any(p.exists() for p in paths):
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# OPS-005  MissingContribGuide
# ---------------------------------------------------------------


class MissingContribGuide(Rule):
    """Detect projects without a CONTRIBUTING.md guide.

    Principles: #11 (The reader is the user).
    Source: ARCH90 — the contributor is a future reader who has none of the maintainer's context.
    """

    code = "OPS-005"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no CONTRIBUTING.md"
    recommendation_template = (
        "Add CONTRIBUTING.md documenting the PR workflow, branch naming, and review process."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        paths = [
            context.root / "CONTRIBUTING.md",
            context.root / "contributing.md",
        ]
        if any(p.exists() for p in paths):
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# OPS-008  HardcodedPortOrHost
# ---------------------------------------------------------------


_HOST_LITERALS = frozenset({"0.0.0.0", "127.0.0.1", "localhost", "::", "::1"})
_EXEMPT_FILENAMES = frozenset({"config.py", "settings.py", "conftest.py"})
_EXEMPT_DIR_NAMES = frozenset({"config", "settings", "tests", "test"})


def _call_display_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return "<call>"


def _is_exempt_path(relative_path: str) -> bool:
    """Config and test files may legitimately bind literal host/port values."""
    norm = relative_path.replace("\\", "/")
    parts = norm.split("/")
    name = parts[-1]
    if name in _EXEMPT_FILENAMES or name.startswith("test_"):
        return True
    return any(part in _EXEMPT_DIR_NAMES for part in parts[:-1])


class HardcodedPortOrHost(Rule):
    """Detect server bind calls that use literal host or port values.

    Principles: #6 (Configuration is a boundary, not a literal),
    #11 (The reader is the user — a hardcoded bind hides the deploy contract).
    Source: 12-Factor App III (Config), Nygard *Release It!* Ch. 17.
    """

    code = "OPS-008"
    severity = Severity.WARN
    category = Category.OPERATIONS
    message_template = (
        "Hardcoded {kind} {value!r} passed to {call}() at line {line}"
    )
    recommendation_template = (
        "Read host and port from configuration (env var, settings module),"
        " not from a literal. Hardcoded binds resist deployment to staging,"
        " containers, or alternate ports and hide the deploy contract from"
        " the reader."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            if _is_exempt_path(fi.relative_path):
                continue
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                call_name = _call_display_name(node)
                for kw in node.keywords:
                    finding = self._check_keyword(fi.relative_path, call_name, kw)
                    if finding is not None:
                        findings.append(finding)
        return findings

    def _check_keyword(
        self, relative_path: str, call_name: str, kw: ast.keyword
    ) -> Finding | None:
        if kw.arg not in {"host", "port"}:
            return None
        value_node = kw.value
        if not isinstance(value_node, ast.Constant):
            return None
        value = value_node.value
        if kw.arg == "host":
            if not isinstance(value, str) or value not in _HOST_LITERALS:
                return None
        else:  # port
            # bool is a subclass of int -- exclude it explicitly.
            if isinstance(value, bool) or not isinstance(value, int):
                return None
        return self.finding(
            file=relative_path,
            line=value_node.lineno,
            kind=kw.arg,
            value=value,
            call=call_name,
        )


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

OPS_RULES = (
    MissingPrecommit(),
    MissingPRTemplate(),
    MissingCodeowners(),
    MissingContribGuide(),
    HardcodedPortOrHost(),
)
