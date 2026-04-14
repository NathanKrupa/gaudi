# ABOUTME: Shared AST helpers for Python pack rules.
# ABOUTME: Generalizes patterns like receiver-variable tracking across rules.
from __future__ import annotations

import ast
from collections.abc import Sequence


def collect_receiver_names(
    tree: ast.Module,
    module: str,
    constructors: Sequence[str],
) -> set[str]:
    """Collect variable names bound to ``module.<constructor>(...)`` calls.

    Walks both ``x = module.ctor(...)`` assignments and
    ``with module.ctor(...) as x:`` context managers, returning the set of
    variable names that hold the resulting receiver. Only direct attribute
    access on a bare ``ast.Name`` matching ``module`` is matched; aliased
    imports and indirect assignments are intentionally out of scope.
    """
    ctor_set = frozenset(constructors)
    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            call = node.value
            if isinstance(call, ast.Call) and _matches_module_ctor(call.func, module, ctor_set):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
        elif isinstance(node, ast.With):
            for item in node.items:
                ctx = item.context_expr
                if (
                    isinstance(ctx, ast.Call)
                    and _matches_module_ctor(ctx.func, module, ctor_set)
                    and isinstance(item.optional_vars, ast.Name)
                ):
                    names.add(item.optional_vars.id)

    return names


def _matches_module_ctor(
    func: ast.expr, module: str, constructors: frozenset[str]
) -> bool:
    return (
        isinstance(func, ast.Attribute)
        and func.attr in constructors
        and isinstance(func.value, ast.Name)
        and func.value.id == module
    )
