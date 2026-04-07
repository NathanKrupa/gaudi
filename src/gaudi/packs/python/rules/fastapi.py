# ABOUTME: FastAPI-specific architectural rules for Gaudi Python pack.
# ABOUTME: Covers missing response_model on endpoints via AST analysis.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext

_ROUTE_METHODS = frozenset({"get", "post", "put", "patch", "delete"})


class FastAPINoResponseModel(Rule):
    code = "FAPI-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "fastapi"
    message_template = "FastAPI endpoint without response_model at line {line}"
    recommendation_template = (
        "Add response_model parameter to endpoints for automatic validation, "
        "serialization, and OpenAPI documentation."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("fastapi"):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for decorator in node.decorator_list:
                    if self._is_route_decorator(decorator):
                        if not self._has_response_model(decorator):
                            findings.append(
                                self.finding(file=f.relative_path, line=decorator.lineno)
                            )
        return findings

    @staticmethod
    def _is_route_decorator(node: ast.expr) -> bool:
        """Check if decorator is @something.get/post/put/patch/delete(...)."""
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        return isinstance(func, ast.Attribute) and func.attr in _ROUTE_METHODS

    @staticmethod
    def _has_response_model(call: ast.Call) -> bool:
        """Check if a decorator call includes response_model keyword."""
        return any(kw.arg == "response_model" for kw in call.keywords)


FASTAPI_RULES = (FastAPINoResponseModel(),)
