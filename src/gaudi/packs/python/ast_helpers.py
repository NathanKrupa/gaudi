# ABOUTME: Shared AST helpers for Python pack rules.
# ABOUTME: Generalizes patterns like receiver-variable tracking across rules.
from __future__ import annotations

import ast
from collections.abc import Sequence


# Every method a stdlib logger exposes for emitting a record. A rule that
# reasons about "did this handler log?" must not key on the level: the level
# describes how loudly the author felt about the failure, not whether the
# failure was handled.
LOG_METHODS: frozenset[str] = frozenset(
    {
        "debug",
        "info",
        "warning",
        "warn",
        "error",
        "exception",
        "critical",
        "fatal",
        "log",
    }
)


def is_logger_call(call: ast.Call) -> bool:
    """True when ``call`` looks like ``<something>.<level>(...)`` on a logger."""
    func = call.func
    return isinstance(func, ast.Attribute) and func.attr in LOG_METHODS


# Modules whose call surface reaches the network, and the methods on them that
# do. `urlopen` is listed separately because urllib names the operation rather
# than the verb.
HTTP_CLIENT_MODULES: frozenset[str] = frozenset({"requests", "httpx", "urllib3", "urllib"})
HTTP_CLIENT_METHODS: frozenset[str] = frozenset(
    {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "request",
        "send",
        "urlopen",
    }
)


def attr_root(node: ast.expr) -> str | None:
    """Walk an Attribute chain to its root Name and return that name."""
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def is_http_client_call(call: ast.Call) -> bool:
    """True for ``requests.post(...)``, ``httpx.get(...)``, ``urllib.request.urlopen(...)``.

    Deliberately shallow: the receiver's *root* name must be a known HTTP client
    module. A session object bound from one (``s = requests.Session()``) is not
    tracked, because a rule that guesses wrong about a receiver produces the
    false positives that get the whole rule disabled.
    """
    func = call.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in HTTP_CLIENT_METHODS:
        return False
    return attr_root(func.value) in HTTP_CLIENT_MODULES


def describe_call(call: ast.Call) -> str:
    """Render ``root.method`` for a finding message."""
    func = call.func
    if isinstance(func, ast.Attribute):
        return f"{attr_root(func.value) or '?'}.{func.attr}"
    return "http call"


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


def _matches_module_ctor(func: ast.expr, module: str, constructors: frozenset[str]) -> bool:
    return (
        isinstance(func, ast.Attribute)
        and func.attr in constructors
        and isinstance(func.value, ast.Name)
        and func.value.id == module
    )
