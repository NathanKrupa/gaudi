# ABOUTME: FastAPI-specific architectural rules for Gaudi Python pack.
# ABOUTME: Covers missing response_model on endpoints.
from __future__ import annotations

import re

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class FastAPINoResponseModel(Rule):
    code = "FAPI-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "fastapi"
    message_template = "FastAPI endpoint without response_model at line {line}"
    recommendation_template = (
        "Add response_model parameter to endpoints for automatic validation, "
        "serialization, and OpenAPI documentation."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("fastapi"):
                continue
            source = f.source
            if not source:
                continue
            pattern = re.compile(r"@\w+\.(get|post|put|patch|delete)\s*\(")
            for i, line in enumerate(source.splitlines(), 1):
                if pattern.search(line) and "response_model" not in line:
                    # Check next few lines for response_model
                    block = "\n".join(source.splitlines()[i - 1 : i + 3])
                    if "response_model" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


FASTAPI_RULES = (FastAPINoResponseModel(),)
