# ABOUTME: Django REST Framework architectural rules for Gaudí Python pack.
# ABOUTME: Covers missing permission classes and throttling on ViewSets via AST.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext

_DRF_BASES = frozenset({"ViewSet", "ModelViewSet", "GenericViewSet", "APIView", "GenericAPIView"})


def _has_drf_base(cls: ast.ClassDef) -> bool:
    """Check if a class inherits from a DRF ViewSet or APIView."""
    return any(
        (isinstance(b, ast.Name) and b.id in _DRF_BASES)
        or (isinstance(b, ast.Attribute) and b.attr in _DRF_BASES)
        for b in cls.bases
    )


def _has_class_attr(cls: ast.ClassDef, attr_name: str) -> bool:
    """Check if a class defines a specific attribute."""
    for item in cls.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == attr_name:
                    return True
    return False


class DRFNoPermissionClass(Rule):
    code = "DRF-SEC-001"
    severity = Severity.WARN
    category = Category.SECURITY
    requires_library = "drf"
    message_template = "ViewSet without explicit permission_classes in '{file}'"
    recommendation_template = (
        "Set permission_classes on every ViewSet. Relying on DEFAULT_PERMISSION_CLASSES "
        "is fragile — a settings change could expose all endpoints."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("rest_framework"):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and _has_drf_base(node):
                    if not _has_class_attr(node, "permission_classes"):
                        findings.append(self.finding(file=f.relative_path))
        return findings


class DRFNoThrottling(Rule):
    code = "DRF-SCALE-001"
    severity = Severity.INFO
    category = Category.SCALABILITY
    requires_library = "drf"
    message_template = "API view without throttle_classes in '{file}'"
    recommendation_template = (
        "Add throttle_classes to prevent abuse. Public APIs without rate limiting "
        "are vulnerable to DDoS and abuse."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("rest_framework"):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and _has_drf_base(node):
                    if not _has_class_attr(node, "throttle_classes"):
                        findings.append(self.finding(file=f.relative_path))
        return findings


DRF_RULES = (DRFNoPermissionClass(), DRFNoThrottling())
