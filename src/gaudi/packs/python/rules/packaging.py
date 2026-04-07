# ABOUTME: Project shape rules for Python packaging and dependency management.
# ABOUTME: Checks pyproject.toml, entry points, lock files, and sys.path hacks.
from __future__ import annotations

import ast
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# STRUCT-010  PathHacks
# ---------------------------------------------------------------


class PathHacks(Rule):
    code = "STRUCT-010"
    severity = Severity.ERROR
    category = Category.STRUCTURE
    message_template = "sys.path manipulation at line {line}"
    recommendation_template = (
        "Use proper packaging (pyproject.toml + pip install -e .) instead of sys.path hacks."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr not in ("insert", "append"):
                    continue
                val = func.value
                if (
                    isinstance(val, ast.Attribute)
                    and val.attr == "path"
                    and isinstance(val.value, ast.Name)
                    and val.value.id == "sys"
                ):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# STRUCT-011  MissingPyproject
# ---------------------------------------------------------------


class MissingPyproject(Rule):
    code = "STRUCT-011"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "Project has no pyproject.toml"
    recommendation_template = (
        "Add a pyproject.toml for modern Python packaging,"
        " dependency management, and tool configuration."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        if not (context.root / "pyproject.toml").exists():
            return [self.finding()]
        return []


# ---------------------------------------------------------------
# STRUCT-012  NoEntryPoint
# ---------------------------------------------------------------


class NoEntryPoint(Rule):
    code = "STRUCT-012"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "Script '{file}' has CLI logic but no entry point in pyproject.toml"
    recommendation_template = (
        "Register this script as a console_scripts entry point in pyproject.toml."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            has_cli_import = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("argparse", "click"):
                            has_cli_import = True
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split(".")[0] in ("argparse", "click"):
                        has_cli_import = True
            if not has_cli_import:
                continue
            has_main_guard = False
            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue
                test = node.test
                if isinstance(test, ast.Compare):
                    left = test.left
                    if (
                        isinstance(left, ast.Name)
                        and left.id == "__name__"
                        and test.comparators
                        and isinstance(test.comparators[0], ast.Constant)
                        and test.comparators[0].value == "__main__"
                    ):
                        has_main_guard = True
                        break
            if has_main_guard:
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                    )
                )
        return findings


# ---------------------------------------------------------------
# STRUCT-013  NoLockFile
# ---------------------------------------------------------------

_LOCK_FILES = (
    "requirements-lock.txt",
    "poetry.lock",
    "Pipfile.lock",
    "pdm.lock",
)


class NoLockFile(Rule):
    code = "STRUCT-013"
    severity = Severity.INFO
    category = Category.STRUCTURE
    message_template = "Project has no dependency lock file"
    recommendation_template = (
        "Add a lock file (pip freeze > requirements-lock.txt)"
        " to pin exact dependency versions"
        " for reproducible builds."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        root = context.root
        for name in _LOCK_FILES:
            if (root / name).exists():
                return []
        return [self.finding()]


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

PACKAGING_RULES = (
    PathHacks(),
    MissingPyproject(),
    NoEntryPoint(),
    NoLockFile(),
)
