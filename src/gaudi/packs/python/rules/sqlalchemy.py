# ABOUTME: SQLAlchemy-specific architectural rules for Gaudi Python pack.
# ABOUTME: Covers default lazy loading (N+1 prevention).
from __future__ import annotations

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
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "relationship(" in line and "lazy=" not in line:
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


SQLALCHEMY_RULES = (SQLAlchemyLazyDefault(),)
