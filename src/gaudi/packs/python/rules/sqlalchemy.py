# ABOUTME: SQLAlchemy-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers session leaks and default lazy loading.
from __future__ import annotations

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class SQLAlchemySessionLeak(Rule):
    code = "SA-ARCH-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "Session created without context manager at line {line}"
    recommendation_template = (
        "Use 'with Session() as session:' or a dependency injection pattern. "
        "Leaked sessions cause connection pool exhaustion."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("sqlalchemy"):
                continue
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "Session()" in line and "with " not in line and "yield" not in line:
                    if "session" in line.lower() and "=" in line:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class SQLAlchemyLazyDefault(Rule):
    code = "SA-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
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


SQLALCHEMY_RULES = (SQLAlchemySessionLeak(), SQLAlchemyLazyDefault())
