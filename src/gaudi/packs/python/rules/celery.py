# ABOUTME: Celery-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers missing retry configuration and time limits on tasks.
from __future__ import annotations

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class CeleryNoRetry(Rule):
    code = "CELERY-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "celery"
    message_template = "Celery task without retry configuration at line {line}"
    recommendation_template = (
        "Add autoretry_for, max_retries, and retry_backoff to tasks that call external services. "
        "Tasks without retry config fail permanently on transient errors."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("celery"):
                continue
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "@" in line and (".task" in line or "shared_task" in line):
                    block = "\n".join(source.splitlines()[max(0, i - 1) : i + 5])
                    if "retry" not in block and "max_retries" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class CeleryNoTimeLimit(Rule):
    code = "CELERY-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    requires_library = "celery"
    message_template = "Celery task without time limit at line {line}"
    recommendation_template = (
        "Add time_limit and soft_time_limit to prevent runaway tasks from consuming workers."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("celery"):
                continue
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "@" in line and (".task" in line or "shared_task" in line):
                    block = "\n".join(source.splitlines()[max(0, i - 1) : i + 5])
                    if "time_limit" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


CELERY_RULES = (CeleryNoRetry(), CeleryNoTimeLimit())
