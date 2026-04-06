# ABOUTME: Flask-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers missing application factory pattern.
from __future__ import annotations

import re

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class FlaskNoAppFactory(Rule):
    code = "FLASK-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
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
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if re.match(r"^app\s*=\s*Flask\s*\(", stripped):
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


FLASK_RULES = [FlaskNoAppFactory()]
