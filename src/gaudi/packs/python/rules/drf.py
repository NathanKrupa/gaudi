# ABOUTME: Django REST Framework architectural rules for Gaudí Python pack.
# ABOUTME: Covers missing permission classes and throttling on ViewSets.
from __future__ import annotations

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


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
            source = f.source
            if not source:
                continue
            if ("ViewSet" in source or "APIView" in source) and "permission_classes" not in source:
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
            source = f.source
            if not source:
                continue
            if ("ViewSet" in source or "APIView" in source) and "throttle_classes" not in source:
                findings.append(self.finding(file=f.relative_path))
        return findings


DRF_RULES = (DRFNoPermissionClass(), DRFNoThrottling())
