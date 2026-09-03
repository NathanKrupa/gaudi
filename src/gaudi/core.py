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
    COMPLEXITY = "complexity"
    CONCURRENCY = "concurrency"
    DOMAIN_MODEL = "domain_model"
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
    Category.COMPLEXITY: "CPLX",
    Category.CONCURRENCY: "ASYNC",
    Category.DOMAIN_MODEL: "DOM",
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
    philosophy_scope: frozenset[str] = field(default_factory=frozenset)

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
        if self.philosophy_scope and "universal" not in self.philosophy_scope:
            d["philosophy_scope"] = sorted(self.philosophy_scope)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @property
    def scope_label(self) -> str:
        """Human-readable scope label, empty for universal rules."""
        if not self.philosophy_scope or "universal" in self.philosophy_scope:
            return ""
        return ", ".join(sorted(self.philosophy_scope))

    def with_severity(self, severity: "Severity") -> "Finding":
        """Return a copy with the severity replaced (for config overrides)."""
        from dataclasses import replace

        return replace(self, severity=severity)

    def format_human(self) -> str:
        severity_tag = self.severity.value.upper()
        location = ""
        if self.file:
            location = f" {self.file}"
            if self.line:
                location += f":{self.line}"

        scope = f" ({self.scope_label})" if self.scope_label else ""
        lines = [f"{self.code} [{severity_tag}]{scope}{location} - {self.message}"]
        if self.recommendation:
            lines.append(f"  -> {self.recommendation}")
        return "\n".join(lines)


@dataclass(frozen=True)
class FileSkip:
    """A file the parser could not read, and why.

    A skip is not a finding: nothing was measured about the file at all. It
    travels on its own channel precisely so "could not look" can never be
    mistaken for "found nothing" — in the report, in the JSON, or in the
    exit code.
    """

    file: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"file": self.file, "reason": self.reason}


@dataclass(frozen=True)
class PackError:
    """A pack that failed to load, and why.

    Like a :class:`FileSkip` this is the absence of evidence rather than a
    finding: every rule the pack owns went unasked. It differs only in scope —
    not one file the parser could not read, but a whole rule catalog that never
    ran. It travels on its own channel for the same reason.

    Every command that reads the pack registry carries it: ``check`` (text,
    json, github, the ``summary`` field, and exit 2 under ``--exit-code``),
    ``count`` and ``report`` (exit 2, unconditionally), ``list-packs``, and
    ``cheat-sheet``, which refuses to render a catalog it could not build.
    Naming a failed pack with ``--pack`` exits 2 rather than reporting it as an
    unknown pack, and reports it in whatever format the caller asked for.

    It outranks :attr:`CheckResult.examined`: a pack that failed to load is the
    pack that *would* have applied, so a run carrying one is reported as a
    broken install rather than as a path no language pack covers.
    """

    pack: str
    error: str

    def to_dict(self) -> dict[str, Any]:
        return {"pack": self.pack, "error": self.error}


@dataclass(frozen=True)
class CheckResult:
    """Everything one ``check`` run learned: what it found, and what it could not read.

    ``examined`` is the third kind of "could not look", and the widest: not one
    file the parser could not read, nor one rule catalog that never loaded, but
    a path no installed pack claims at all. It carries no rows because there is
    nothing to enumerate — the whole run is the absence. It defaults to ``True``
    so a pack's own result, which by construction examined what it was given,
    says so without asking.
    """

    findings: list[Finding] = field(default_factory=list)
    skipped: list[FileSkip] = field(default_factory=list)
    pack_errors: list[PackError] = field(default_factory=list)
    examined: bool = True


UNIVERSAL_SCOPE: frozenset[str] = frozenset({"universal"})

VALID_SCHOOLS: frozenset[str] = frozenset(
    {
        "classical",
        "pragmatic",
        "functional",
        "unix",
        "resilient",
        "data-oriented",
        "convention",
        "event-sourced",
    }
)

VALID_SCOPE_TOKENS: frozenset[str] = VALID_SCHOOLS | {"universal"}

DEFAULT_SCHOOL: str = "classical"


class Rule:
    """
    Base class for all Gaudí rules.

    Subclass this to create custom architectural checks. Each rule
    must define a code, severity, category, and implement the check() method.

    Every rule also declares a ``philosophy_scope`` — the set of architectural
    schools under which the rule is defensible. The default ``{"universal"}``
    means the rule descends from the three pillars and holds in every school;
    a rule that depends on school-specific axioms should list the schools
    explicitly (e.g. ``{"pragmatic", "functional"}``). See
    ``docs/philosophy/`` for the axiom sheets and ``docs/rule-sources.md``
    for the scope audit.

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
    philosophy_scope: frozenset[str] = UNIVERSAL_SCOPE
    # True when the rule's verdict depends on files other than the one it
    # reports on — a paired test module, a health route declared elsewhere.
    # Pointed at a single file such a rule cannot see the evidence that would
    # clear it, so it fires on every invocation and teaches its consumers to
    # disable it repo-wide. Packs sit these rules out of single-file runs
    # instead.
    requires_project_context: bool = False

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
            philosophy_scope=self.philosophy_scope,
        )
