# ABOUTME: Alembic migration rules for Gaudí Python pack.
# ABOUTME: Covers missing downgrade functions and migration branch divergence via AST.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext

_LIBRARY = "alembic"


def _is_alembic_migration(tree: ast.Module) -> bool:
    """Check if an AST looks like an alembic migration (has module-level `revision` assignment)."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "revision":
                    return True
    return False


def _get_function_body_is_empty(tree: ast.Module, func_name: str) -> bool | None:
    """Return True if function exists but body is empty (pass/Ellipsis), False if non-empty, None if missing."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            body = node.body
            if len(body) == 1:
                stmt = body[0]
                if isinstance(stmt, ast.Pass):
                    return True
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
                    if stmt.value.value is ...:
                        return True
            return False
    return None


def _get_string_assign(tree: ast.Module, var_name: str) -> str | None:
    """Extract a module-level string assignment value."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == var_name:
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        return node.value.value
    return None


class MigrationNoDowngrade(Rule):
    code = "ALM-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = _LIBRARY
    message_template = "Alembic migration {file} has no downgrade path"
    recommendation_template = (
        "Implement downgrade() so migrations can be rolled back. "
        "Irreversible migrations block emergency rollbacks in production."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            if not _is_alembic_migration(tree):
                continue
            result = _get_function_body_is_empty(tree, "downgrade")
            if result is None or result is True:
                findings.append(self.finding(file=f.relative_path))
        return findings


class MultipleHeads(Rule):
    code = "ALM-OPS-001"
    severity = Severity.ERROR
    category = Category.OPERATIONS
    requires_library = _LIBRARY
    message_template = (
        "Multiple alembic migration heads detected — "
        "down_revision {down_revision!r} is shared by {files}"
    )
    recommendation_template = (
        "Merge divergent migration branches with 'alembic merge heads'. "
        "Multiple heads cause 'alembic upgrade head' to fail."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        # Map down_revision -> list of migration files that depend on it
        children: dict[str, list[str]] = {}
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            if not _is_alembic_migration(tree):
                continue
            down_rev = _get_string_assign(tree, "down_revision")
            if down_rev is not None:
                children.setdefault(down_rev, []).append(f.relative_path)

        findings = []
        for down_rev, files in children.items():
            if len(files) > 1:
                findings.append(
                    self.finding(
                        down_revision=down_rev,
                        files=", ".join(sorted(files)),
                    )
                )
        return findings


ALEMBIC_RULES = (MigrationNoDowngrade(), MultipleHeads())
