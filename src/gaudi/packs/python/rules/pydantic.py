# ABOUTME: Pydantic-specific architectural rules for Gaudí Python pack.
# ABOUTME: Covers mutable default values in Pydantic models via AST analysis.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext

_PYDANTIC_BASES = frozenset({"BaseModel", "BaseSettings"})
_PYDANTIC_CLASS_VARS = frozenset({"model_config", "model_fields", "model_validators"})


def _is_pydantic_class(cls: ast.ClassDef) -> bool:
    """Check if a class inherits from BaseModel or BaseSettings."""
    return any(
        (isinstance(b, ast.Name) and b.id in _PYDANTIC_BASES)
        or (isinstance(b, ast.Attribute) and b.attr in _PYDANTIC_BASES)
        for b in cls.bases
    )


class PydanticMutableDefault(Rule):
    """Detect mutable default values in Pydantic models.

    Principles: #5 (State must be visible).
    Source: FWDOCS Pydantic validators — mutable defaults are shared hidden state.
    """

    code = "PYD-ARCH-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    requires_library = "pydantic"
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
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if not _is_pydantic_class(node):
                    continue
                for item in node.body:
                    if not isinstance(item, (ast.Assign, ast.AnnAssign)):
                        continue
                    # Skip Pydantic class variables (model_config, etc.)
                    if isinstance(item, ast.Assign) and any(
                        isinstance(t, ast.Name) and t.id in _PYDANTIC_CLASS_VARS
                        for t in item.targets
                    ):
                        continue
                    value = item.value if isinstance(item, ast.AnnAssign) else item.value
                    if value is None:
                        continue
                    # Skip Field() wrappers — Pydantic handles these safely
                    if isinstance(value, ast.Call) and (
                        (isinstance(value.func, ast.Name) and value.func.id == "Field")
                        or (isinstance(value.func, ast.Attribute) and value.func.attr == "Field")
                    ):
                        continue
                    if isinstance(value, (ast.List, ast.Dict, ast.Set)):
                        findings.append(self.finding(file=f.relative_path, line=item.lineno))
        return findings


PYDANTIC_RULES = (PydanticMutableDefault(),)
