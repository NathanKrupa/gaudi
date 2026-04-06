# ABOUTME: Pydantic-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers mutable default values in Pydantic models.
from __future__ import annotations

import re

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class PydanticMutableDefault(Rule):
    code = "PYD-ARCH-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "Mutable default value in Pydantic model at line {line}"
    recommendation_template = (
        "Use Field(default_factory=list) instead of Field(default=[]) in Pydantic models. "
        "Mutable defaults are shared across instances."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("pydantic"):
                continue
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if re.search(r"=\s*\[\s*\]|=\s*\{\s*\}", line) and "Field(" not in line:
                    if "BaseModel" in source or "BaseSettings" in source:
                        findings.append(self.finding(file=f.relative_path, line=i))
        return findings


PYDANTIC_RULES = (PydanticMutableDefault(),)
