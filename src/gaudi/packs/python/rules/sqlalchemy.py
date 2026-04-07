# ABOUTME: SQLAlchemy-specific architectural rules for Gaudi Python pack.
# ABOUTME: Covers default lazy loading (N+1 prevention) via AST analysis.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class SQLAlchemyLazyDefault(Rule):
    code = "SA-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    requires_library = "sqlalchemy"
    message_template = "relationship() using default lazy loading at line {line}"
    recommendation_template = (
        "Explicitly set lazy='select', 'joined', 'subquery', or 'selectin' on relationships. "
        "Default lazy loading causes N+1 queries."
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
                func = node.func
                is_relationship = (isinstance(func, ast.Name) and func.id == "relationship") or (
                    isinstance(func, ast.Attribute) and func.attr == "relationship"
                )
                if not is_relationship:
                    continue
                if not any(kw.arg == "lazy" for kw in node.keywords):
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


SQLALCHEMY_RULES = (SQLAlchemyLazyDefault(),)
