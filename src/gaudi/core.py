"""
Core data models for Gaudí findings, rules, and severity levels.

These are the building blocks that every language pack uses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(Enum):
    ERROR = "error"
    WARN = "warn"
    INFO = "info"

    @property
    def priority(self) -> int:
        return {Severity.ERROR: 0, Severity.WARN: 1, Severity.INFO: 2}[self]

    @property
    def label(self) -> str:
        return self.value.upper()

    @property
    def style(self) -> str:
        return {
            Severity.ERROR: "bold red",
            Severity.WARN: "bold yellow",
            Severity.INFO: "bold blue",
        }[self]

    def __lt__(self, other: Severity) -> bool:
        return self.priority < other.priority


class Category(Enum):
    ARCHITECTURE = "architecture"
    CODE_SMELL = "code_smell"
    ERROR_HANDLING = "error_handling"
    INDEXING = "indexing"
    LOGGING = "logging"
    OPERATIONS = "operations"
    RELATIONSHIPS = "relationships"
    SCHEMA = "schema"
    SECURITY = "security"
    SCALABILITY = "scalability"
    STABILITY = "stability"
    STRUCTURE = "structure"


# Map category to error code prefix
CATEGORY_PREFIXES = {
    Category.ARCHITECTURE: "ARCH",
    Category.CODE_SMELL: "SMELL",
    Category.ERROR_HANDLING: "ERR",
    Category.INDEXING: "IDX",
    Category.LOGGING: "LOG",
    Category.OPERATIONS: "OPS",
    Category.RELATIONSHIPS: "REL",
    Category.SCHEMA: "SCHEMA",
    Category.SECURITY: "SEC",
    Category.SCALABILITY: "SCALE",
    Category.STABILITY: "STAB",
    Category.STRUCTURE: "STRUCT",
}


@dataclass(frozen=True)
class Finding:
    """
    A single architectural finding — the fundamental output unit of Gaudí.

    Designed to be machine-readable so AI agents can parse, understand,
    and resolve findings without ambiguity.
    """

    code: str
    severity: Severity
    category: Category
    message: str
    recommendation: str
    file: str | None = None
    line: int | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {
            "code": self.code,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "recommendation": self.recommendation,
        }
        if self.file is not None:
            d["file"] = self.file
        if self.line is not None:
            d["line"] = self.line
        if self.context:
            d["context"] = self.context
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def format_human(self) -> str:
        severity_tag = self.severity.value.upper()
        location = ""
        if self.file:
            location = f" {self.file}"
            if self.line:
                location += f":{self.line}"

        lines = [f"{self.code} [{severity_tag}]{location} - {self.message}"]
        if self.recommendation:
            lines.append(f"  -> {self.recommendation}")
        return "\n".join(lines)


class Rule:
    """
    Base class for all Gaudí rules.

    Subclass this to create custom architectural checks. Each rule
    must define a code, severity, category, and implement the check() method.

    Example:
        class CheckTenantIsolation(Rule):
            code = "ARCH-001"
            severity = Severity.ERROR
            category = Category.ARCHITECTURE
            message_template = "Multi-tenant table '{table}' has no tenant isolation column"

            def check(self, context):
                for table in context.models:
                    if table.is_multi_tenant and not table.has_column("tenant_id"):
                        yield self.finding(
                            table=table.name,
                            file=table.source_file,
                            line=table.source_line,
                        )
    """

    code: str = ""
    severity: Severity = Severity.WARN
    category: Category = Category.ARCHITECTURE
    message_template: str = ""
    recommendation_template: str = ""
    requires_library: str | None = None

    def check(self, context: Any) -> list[Finding]:
        """
        Run this rule against the given context.

        Override this method in subclasses. Yield or return Finding objects
        for each violation detected.
        """
        raise NotImplementedError(f"Rule {self.code} must implement check()")

    def finding(
        self,
        file: str | None = None,
        line: int | None = None,
        recommendation: str | None = None,
        **kwargs: Any,
    ) -> Finding:
        """
        Create a Finding from this rule's templates.

        Pass keyword arguments to fill in template placeholders.
        """
        # Merge file/line into format dict so templates can reference {file}
        fmt = dict(kwargs)
        if file is not None:
            fmt.setdefault("file", file)
        if line is not None:
            fmt.setdefault("line", line)

        message = self.message_template.format(**fmt) if fmt else self.message_template
        rec = recommendation or (
            self.recommendation_template.format(**fmt)
            if fmt and self.recommendation_template
            else self.recommendation_template
        )

        return Finding(
            code=self.code,
            severity=self.severity,
            category=self.category,
            message=message,
            recommendation=rec,
            file=file,
            line=line,
            context=kwargs,
        )
