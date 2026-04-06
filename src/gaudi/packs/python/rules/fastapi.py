# ABOUTME: FastAPI-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers missing response_model and synchronous endpoints.
from __future__ import annotations

import re

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class FastAPINoResponseModel(Rule):
    code = "FAPI-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "FastAPI endpoint without response_model at line {line}"
    recommendation_template = (
        "Add response_model parameter to endpoints for automatic validation, "
        "serialization, and OpenAPI documentation."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "fastapi" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            pattern = re.compile(r"@\w+\.(get|post|put|patch|delete)\s*\(")
            for i, line in enumerate(source.splitlines(), 1):
                if pattern.search(line) and "response_model" not in line:
                    # Check next few lines for response_model
                    block = "\n".join(source.splitlines()[i - 1 : i + 3])
                    if "response_model" not in block:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class FastAPISyncEndpoint(Rule):
    code = "FAPI-SCALE-001"
    severity = Severity.INFO
    category = Category.SCALABILITY
    message_template = "Synchronous endpoint function at line {line} — consider async for I/O"
    recommendation_template = (
        "Use async def for endpoints with I/O operations (database, HTTP calls). "
        "Sync endpoints block the event loop thread pool."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if "fastapi" not in str(f.imports):
                continue
            try:
                source = f.path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            lines = source.splitlines()
            for i, line in enumerate(lines, 1):
                if re.search(r"@\w+\.(get|post|put|patch|delete)", line):
                    # Check if next def is sync
                    for j in range(i, min(i + 5, len(lines))):
                        if lines[j - 1].strip().startswith("def ") and "async" not in lines[j - 1]:
                            findings.append(self.finding(file=f.relative_path, line=j))
                            break
        return findings


FASTAPI_RULES = [FastAPINoResponseModel(), FastAPISyncEndpoint()]
