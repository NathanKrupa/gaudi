# ABOUTME: Type annotation and literal hygiene rules.
# ABOUTME: Detects missing return types on public functions and repeated magic strings.
from __future__ import annotations

import ast
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# STRUCT-020  MissingReturnTypes
# ---------------------------------------------------------------


class MissingReturnTypes(Rule):
    code = "STRUCT-020"
    severity = Severity.INFO
    category = Category.STRUCTURE
    message_template = "Public function '{function}' has no return type annotation"
    recommendation_template = (
        "Add return type annotations to public functions"
        " for documentation and type-checker support."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.iter_child_nodes(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                if node.name.startswith("_"):
                    continue
                if node.returns is not None:
                    continue
                if not self._has_return(node):
                    continue
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=node.lineno,
                        function=node.name,
                    )
                )
        return findings

    @staticmethod
    def _has_return(func: ast.FunctionDef) -> bool:
        for child in ast.walk(func):
            if isinstance(child, ast.Return) and (child.value is not None):
                return True
        return False


# ---------------------------------------------------------------
# STRUCT-021  MagicStrings
# ---------------------------------------------------------------

_EXEMPT_STRINGS = frozenset(
    {
        "utf-8",
        "utf8",
        "replace",
        "strict",
        "ignore",
        "ascii",
        "latin-1",
    }
)


class MagicStrings(Rule):
    code = "STRUCT-021"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "String '{value}' appears {count} times — consider using a constant"
    recommendation_template = "Extract repeated string literals into named constants or enums."

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            docstrings = self._collect_docstrings(tree)
            counts: dict[str, int] = {}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant):
                    continue
                if not isinstance(node.value, str):
                    continue
                val = node.value
                if len(val) <= 1 or not val:
                    continue
                if val.lower() in _EXEMPT_STRINGS:
                    continue
                if id(node) in docstrings:
                    continue
                counts[val] = counts.get(val, 0) + 1
            for val, cnt in counts.items():
                if cnt >= 3:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            value=val,
                            count=cnt,
                        )
                    )
        return findings

    @staticmethod
    def _collect_docstrings(
        tree: ast.Module,
    ) -> set[int]:
        ids: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.Module,
                    ast.ClassDef,
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    ids.add(id(node.body[0].value))
        return ids


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

TYPES_RULES = (
    MissingReturnTypes(),
    MagicStrings(),
)
