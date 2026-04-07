# ABOUTME: HTTP requests architectural rules for Gaudi Python pack.
# ABOUTME: Covers missing timeouts for requests library via AST analysis.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext

_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})


class RequestsNoTimeout(Rule):
    """Detect HTTP requests without a timeout parameter.

    Principles: #4 (Failure must be named).
    Source: NYGARD Ch. 5 — Timeouts: every external call has a deadline.
    """

    code = "HTTP-SCALE-001"
    severity = Severity.ERROR
    category = Category.SCALABILITY
    requires_library = "requests"
    message_template = "HTTP request without timeout at line {line}"
    recommendation_template = (
        "Always set a timeout on HTTP requests. Without a timeout, your application "
        "can hang indefinitely waiting for a response."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not self._is_requests_call(node):
                    continue
                if not any(kw.arg == "timeout" for kw in node.keywords):
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings

    @staticmethod
    def _is_requests_call(node: ast.Call) -> bool:
        """Check if node is requests.get/post/etc."""
        func = node.func
        return (
            isinstance(func, ast.Attribute)
            and func.attr in _HTTP_METHODS
            and isinstance(func.value, ast.Name)
            and func.value.id == "requests"
        )


REQUESTS_RULES = (RequestsNoTimeout(),)
