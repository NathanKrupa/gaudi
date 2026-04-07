# ABOUTME: Configuration hygiene rules for environment variable usage.
# ABOUTME: Detects env leakage in class methods and scattered config across files.
from __future__ import annotations

import ast
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# ARCH-020  EnvLeakage
# ---------------------------------------------------------------


class EnvLeakage(Rule):
    code = "ARCH-020"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Class method '{method}' reads environment directly at line {line}"
    recommendation_template = (
        "Accept configuration through __init__ parameters."
        " Only factory functions should read os.getenv()."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for item in node.body:
                    if not isinstance(
                        item,
                        (ast.FunctionDef, ast.AsyncFunctionDef),
                    ):
                        continue
                    method_name = item.name
                    for child in ast.walk(item):
                        if self._is_env_read(child):
                            findings.append(
                                self.finding(
                                    file=fi.relative_path,
                                    line=child.lineno,
                                    method=method_name,
                                )
                            )
        return findings

    @staticmethod
    def _is_env_read(node: ast.AST) -> bool:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if (
                    func.attr == "getenv"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                ):
                    return True
                if func.attr == "get" and isinstance(func.value, ast.Attribute):
                    inner = func.value
                    if (
                        inner.attr == "environ"
                        and isinstance(inner.value, ast.Name)
                        and inner.value.id == "os"
                    ):
                        return True
        if isinstance(node, ast.Subscript):
            val = node.value
            if (
                isinstance(val, ast.Attribute)
                and val.attr == "environ"
                and isinstance(val.value, ast.Name)
                and val.value.id == "os"
            ):
                return True
        return False


# ---------------------------------------------------------------
# ARCH-022  ScatteredConfig
# ---------------------------------------------------------------


class ScatteredConfig(Rule):
    code = "ARCH-022"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "os.getenv()/os.environ used in {count} files — configuration is scattered"
    recommendation_template = (
        "Centralize configuration reading"
        " in a single module. Other modules should"
        " receive config via parameters."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        files_with_env = sum(1 for fi in context.files if self._has_env_access(fi))
        if files_with_env >= 4:
            return [self.finding(count=files_with_env)]
        return []

    @staticmethod
    def _has_env_access(fi) -> bool:
        """Check if a file accesses os.getenv or os.environ via AST."""
        tree = fi.ast_tree
        if tree is None:
            return False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "getenv"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                ):
                    return True
            if isinstance(node, ast.Attribute):
                if (
                    node.attr == "environ"
                    and isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                ):
                    return True
        return False


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

CONFIG_RULES = (
    EnvLeakage(),
    ScatteredConfig(),
)
