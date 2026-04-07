# ABOUTME: Django-specific architectural rules for Gaudi Python pack.
# ABOUTME: Covers SECRET_KEY exposure and DEBUG mode via AST analysis.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class DjangoSecretKeyExposed(Rule):
    code = "DJ-SEC-001"
    severity = Severity.ERROR
    category = Category.SECURITY
    requires_library = "django"
    message_template = "SECRET_KEY appears hardcoded in settings at line {line}"
    recommendation_template = (
        "Load SECRET_KEY from environment variables: SECRET_KEY = os.environ['SECRET_KEY']. "
        "Hardcoded secrets in source control are a critical security vulnerability."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "settings" not in f.relative_path.lower():
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SECRET_KEY":
                        if isinstance(node.value, ast.Constant) and isinstance(
                            node.value.value, str
                        ):
                            findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


class DjangoDebugTrue(Rule):
    code = "DJ-SEC-002"
    severity = Severity.ERROR
    category = Category.SECURITY
    requires_library = "django"
    message_template = "DEBUG = True in production settings at line {line}"
    recommendation_template = (
        "Set DEBUG = False in production. Use environment variables to control debug mode."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "settings" not in f.relative_path.lower():
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "DEBUG":
                        if isinstance(node.value, ast.Constant) and node.value.value is True:
                            findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


DJANGO_LIB_RULES = (DjangoSecretKeyExposed(), DjangoDebugTrue())
