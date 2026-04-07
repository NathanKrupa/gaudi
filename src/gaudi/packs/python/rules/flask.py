# ABOUTME: Flask-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers missing application factory pattern via AST analysis.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class FlaskNoAppFactory(Rule):
    code = "FLASK-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    requires_library = "flask"
    message_template = "Flask app created at module level — use application factory pattern"
    recommendation_template = (
        "Use create_app() factory function instead of module-level Flask(). "
        "Factories enable testing, multiple configs, and blueprint registration."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("flask"):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if not (isinstance(target, ast.Name) and target.id == "app"):
                        continue
                    if isinstance(node.value, ast.Call):
                        func = node.value.func
                        if (isinstance(func, ast.Name) and func.id == "Flask") or (
                            isinstance(func, ast.Attribute) and func.attr == "Flask"
                        ):
                            findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


FLASK_RULES = (FlaskNoAppFactory(),)
