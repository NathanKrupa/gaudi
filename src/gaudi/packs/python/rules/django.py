# ABOUTME: Django-specific architectural rules for Gaudi Python pack.
# ABOUTME: Covers SECRET_KEY exposure and DEBUG mode.
from __future__ import annotations

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
            source = f.source
            if not source:
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
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                stripped = line.strip()
                if stripped == "DEBUG = True" or stripped == "DEBUG=True":
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


DJANGO_LIB_RULES = (DjangoSecretKeyExposed(), DjangoDebugTrue())
