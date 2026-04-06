# ABOUTME: Error handling rules for exception hygiene.
# ABOUTME: Detects bare/broad except clauses and errors logged without re-raising.
from __future__ import annotations

import ast
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# ERR-001  BareExcept
# ---------------------------------------------------------------


class BareExcept(Rule):
    code = "ERR-001"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = "Broad exception handler at line {line} swallows errors"
    recommendation_template = (
        "Catch specific exceptions. If you must catch broadly, re-raise after handling."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                is_bare = node.type is None
                is_broad = isinstance(node.type, ast.Name) and node.type.id == "Exception"
                if not (is_bare or is_broad):
                    continue
                if self._body_has_raise(node.body):
                    continue
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=node.lineno,
                    )
                )
        return findings

    @staticmethod
    def _body_has_raise(body: list[ast.stmt]) -> bool:
        for child in ast.walk(ast.Module(body=body)):
            if isinstance(child, ast.Raise):
                return True
        return False


# ---------------------------------------------------------------
# ERR-003  ErrorSwallowing
# ---------------------------------------------------------------


class ErrorSwallowing(Rule):
    code = "ERR-003"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = "Error logged but not re-raised at line {line}"
    recommendation_template = (
        "Logging an error without re-raising hides failures."
        " Log and re-raise, or handle the error explicitly."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                has_log = False
                has_raise = False
                for child in ast.walk(ast.Module(body=node.body)):
                    if isinstance(child, ast.Raise):
                        has_raise = True
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Attribute) and func.attr in ("error", "exception"):
                            has_log = True
                if has_log and not has_raise:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

ERRORS_RULES = (
    BareExcept(),
    ErrorSwallowing(),
)
