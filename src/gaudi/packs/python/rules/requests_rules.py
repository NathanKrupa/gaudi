# ABOUTME: HTTP requests architectural rules for Gaudí Python pack.
# ABOUTME: Covers missing timeouts and retry logic for requests library.
from __future__ import annotations

import re

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class RequestsNoTimeout(Rule):
    code = "HTTP-SCALE-001"
    severity = Severity.ERROR
    category = Category.SCALABILITY
    message_template = "HTTP request without timeout at line {line}"
    recommendation_template = (
        "Always set a timeout on HTTP requests. Without a timeout, your application "
        "can hang indefinitely waiting for a response."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            source = f.source
            if not source:
                continue
            pattern = re.compile(r"requests\.(get|post|put|patch|delete|head|options)\s*\(")
            for i, line in enumerate(source.splitlines(), 1):
                if pattern.search(line) and "timeout" not in line:
                    # Check next few lines too
                    block = "\n".join(source.splitlines()[i - 1 : i + 3])
                    if "timeout" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class RequestsNoRetry(Rule):
    code = "HTTP-ARCH-001"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = "HTTP calls without retry logic in '{file}'"
    recommendation_template = (
        "Use urllib3.util.Retry with requests.Session for automatic retries on transient failures."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("requests"):
                continue
            source = f.source
            if not source:
                continue
            if "requests.get" in source or "requests.post" in source:
                if "Retry" not in source and "retry" not in source and "tenacity" not in source:
                    findings.append(self.finding(file=f.relative_path))
        return findings


REQUESTS_RULES = (RequestsNoTimeout(), RequestsNoRetry())
