# ABOUTME: Pandas-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers inplace anti-pattern and iterrows performance.
from __future__ import annotations

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class PandasInplaceAntiPattern(Rule):
    code = "PD-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "inplace=True used at line {line} — this is deprecated and error-prone"
    recommendation_template = (
        "Use df = df.method() instead of df.method(inplace=True). "
        "inplace breaks method chaining and is planned for deprecation."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            if not f.has_import("pandas"):
                continue
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if "inplace=True" in line:
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


class PandasIterrows(Rule):
    code = "PD-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    message_template = "iterrows() at line {line} — use vectorized operations instead"
    recommendation_template = (
        "iterrows() is extremely slow. Use .apply(), vectorized operations, "
        "or .itertuples() (10-100x faster) instead."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            source = f.source
            if not source:
                continue
            for i, line in enumerate(source.splitlines(), 1):
                if ".iterrows()" in line:
                    findings.append(self.finding(file=f.relative_path, line=i))
        return findings


PANDAS_RULES = (PandasInplaceAntiPattern(), PandasIterrows())
