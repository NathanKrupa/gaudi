# ABOUTME: HTTP requests architectural rules for Gaudi Python pack.
# ABOUTME: Covers missing timeouts for requests library.
from __future__ import annotations

import re

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class RequestsNoTimeout(Rule):
    code = "HTTP-SCALE-001"
    severity = Severity.ERROR
    category = Category.SCALABILITY
    requires_library = "requests"
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
                    block = "\n".join(source.splitlines()[i - 1 : i + 3])
                    if "timeout" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


REQUESTS_RULES = (RequestsNoTimeout(),)
