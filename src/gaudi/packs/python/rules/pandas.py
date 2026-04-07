# ABOUTME: Pandas-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers inplace anti-pattern and iterrows performance via AST.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


class PandasInplaceAntiPattern(Rule):
    """Detect pandas inplace=True usage.

    Principles: #5 (State must be visible).
    Source: FWDOCS Pandas deprecation guidance — inplace mutates hidden state.
    """

    code = "PD-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "pandas"
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
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                for kw in node.keywords:
                    if (
                        kw.arg == "inplace"
                        and isinstance(kw.value, ast.Constant)
                        and kw.value.value is True
                    ):
                        findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


class PandasIterrows(Rule):
    """Detect pandas iterrows() usage.

    Principles: #4 (Failure must be named).
    Source: FWDOCS Pandas vectorization — row iteration fails under production data sizes.
    """

    code = "PD-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    requires_library = "pandas"
    message_template = "iterrows() at line {line} — use vectorized operations instead"
    recommendation_template = (
        "iterrows() is extremely slow. Use .apply(), vectorized operations, "
        "or .itertuples() (10-100x faster) instead."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "iterrows"
                ):
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


PANDAS_RULES = (PandasInplaceAntiPattern(), PandasIterrows())
