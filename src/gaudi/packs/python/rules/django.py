# ABOUTME: Django-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers SECRET_KEY exposure, DEBUG mode, and fat views.
from __future__ import annotations

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class DjangoSecretKeyExposed(Rule):
    code = "DJ-SEC-001"
    severity = Severity.ERROR
    category = Category.SECURITY
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
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if (
                    "SECRET_KEY" in line
                    and ("'" in line or '"' in line)
                    and "os.environ" not in line
                    and "env(" not in line
                ):
                    if not line.strip().startswith("#"):
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class DjangoDebugTrue(Rule):
    code = "DJ-SEC-002"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = "DEBUG = True in production settings at line {line}"
    recommendation_template = (
        "Set DEBUG = False in production. Use environment variables to control debug mode."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "settings" not in f.relative_path.lower():
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if stripped == "DEBUG = True" or stripped == "DEBUG=True":
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class DjangoFatView(Rule):
    code = "DJ-STRUCT-001"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "View file '{file}' is {lines} lines — extract business logic to services"
    recommendation_template = (
        "Views should be thin. Move business logic to service functions or model methods."
    )
    THRESHOLD = 300

    def check(self, context: PythonContext) -> list[Finding]:
        if context.framework != "django":
            return []
        findings = []
        for f in context.files:
            if "views" in f.relative_path.lower() and f.line_count > self.THRESHOLD:
                findings.append(self.finding(file=f.relative_path, lines=f.line_count))
        return findings


DJANGO_LIB_RULES = [DjangoSecretKeyExposed(), DjangoDebugTrue(), DjangoFatView()]
