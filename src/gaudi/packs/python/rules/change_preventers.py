# ABOUTME: Fowler "change preventers" code smells: structures that resist modification.
# ABOUTME: Divergent change, shotgun surgery, duplicated code.
from __future__ import annotations

import ast
import copy

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.ast_helpers import is_test_path
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# SMELL-007  DivergentChange
# ---------------------------------------------------------------


def _method_attr_set(
    method: ast.FunctionDef,
) -> set[str]:
    """Collect self.xxx attribute names accessed in a method."""
    attrs: set[str] = set()
    for node in ast.walk(method):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
        ):
            attrs.add(node.attr)
    return attrs


def _init_injected_attrs(cls: ast.ClassDef) -> set[str]:
    """Attributes set in __init__ directly from constructor parameters.

    When __init__ does ``self.x = x`` (parameter name matches attribute
    name), that attribute is a dependency injected at construction time,
    not internal state. Disjoint groups formed entirely from injected
    dependencies indicate a coordinator/orchestrator pattern, not
    divergent change.
    """
    for node in cls.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "__init__":
            continue
        param_names = {arg.arg for arg in node.args.args if arg.arg != "self"}
        injected: set[str] = set()
        for stmt in ast.walk(node):
            if (
                isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Attribute)
                and isinstance(stmt.targets[0].value, ast.Name)
                and stmt.targets[0].value.id == "self"
                and isinstance(stmt.value, ast.Name)
                and stmt.value.id in param_names
            ):
                injected.add(stmt.targets[0].attr)
        return injected
    return set()


def _is_private_method(name: str) -> bool:
    """A ``_name`` or name-mangled ``__name`` helper; never a ``__dunder__`` hook."""
    is_dunder = name.startswith("__") and name.endswith("__")
    return name.startswith("_") and not is_dunder


def _link_private_helpers(
    methods: list[ast.FunctionDef],
    attr_sets: list[set[str]],
) -> list[set[str]]:
    """Join each private helper to the methods that call it.

    A ``self._step()`` call puts ``_step`` in the caller's set; adding
    ``_step`` to the helper's own set makes caller and callee share it, so a
    pipeline of extracted private helpers reads as one group (gaudi#281).
    A public method is its own entry point, so calling one joins nothing, and
    a private method no other method names gains nothing it could be joined by.
    """
    referenced = set().union(*attr_sets) if attr_sets else set()
    return [
        s | {m.name} if _is_private_method(m.name) and m.name in referenced else s
        for m, s in zip(methods, attr_sets)
    ]


class DivergentChange(Rule):
    """SMELL-007: Class methods touch disjoint attribute sets.

    Principles: #2 (One concept, one home), #7 (Layers must earn their existence).
    Source: FOWLER Ch. 3 — Divergent Change.
    """

    code = "SMELL-007"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Class '{class_name}' has methods touching disjoint attribute sets"
    recommendation_template = (
        "Split the class into focused classes, each handling one set of related attributes."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                if len(methods) < 4:
                    continue
                injected = _init_injected_attrs(node)
                non_init = [m for m in methods if m.name != "__init__"]
                attr_sets = _link_private_helpers(
                    non_init, [_method_attr_set(m) - injected for m in non_init]
                )
                # Remove empty sets
                attr_sets = [s for s in attr_sets if s]
                if len(attr_sets) < 2:
                    continue
                if self._has_disjoint_groups(attr_sets):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
                        )
                    )
        return findings

    def _has_disjoint_groups(
        self,
        attr_sets: list[set[str]],
    ) -> bool:
        """Check if there are 2+ groups sharing zero attrs."""
        # Union-find via simple clustering
        groups: list[set[str]] = []
        for s in attr_sets:
            merged = False
            for g in groups:
                if g & s:
                    g |= s
                    merged = True
                    break
            if not merged:
                groups.append(set(s))
        # Merge groups that now overlap after additions
        changed = True
        while changed:
            changed = False
            new_groups: list[set[str]] = []
            for g in groups:
                placed = False
                for ng in new_groups:
                    if ng & g:
                        ng |= g
                        placed = True
                        changed = True
                        break
                if not placed:
                    new_groups.append(g)
            groups = new_groups
        return len(groups) >= 2


# ---------------------------------------------------------------
# SMELL-008  ShotgunSurgery
# ---------------------------------------------------------------


class ShotgunSurgery(Rule):
    """SMELL-008: Module-level name used in 4+ functions.

    Principles: #2 (One concept, one home).
    Source: FOWLER Ch. 3 — Shotgun Surgery.
    """

    code = "SMELL-008"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = (
        "'{name}' is referenced in {count} functions — changing it requires shotgun surgery"
    )
    recommendation_template = (
        "Centralize usage behind a single function or class to reduce the blast radius of changes."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            # Find module-level names
            module_names: set[str] = set()
            for node in tree.body:
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name):
                            module_names.add(t.id)
            if not module_names:
                continue
            # Count references per function
            funcs = [
                n
                for n in tree.body
                if isinstance(
                    n,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                )
            ]
            name_users: dict[str, int] = {}
            for fn in funcs:
                used_in_fn: set[str] = set()
                for node in ast.walk(fn):
                    if isinstance(node, ast.Name) and node.id in module_names:
                        used_in_fn.add(node.id)
                for name in used_in_fn:
                    name_users[name] = name_users.get(name, 0) + 1
            for name, count in name_users.items():
                if count >= 4:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=1,
                            name=name,
                            count=count,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-002  DuplicatedCode
# ---------------------------------------------------------------


# A function body with fewer AST nodes than this is too small for two copies
# to count as duplicated logic: one- and two-statement wrappers share shapes by
# accident. Docstrings and expression-context markers are not counted.
_MIN_BODY_NODES = 15


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    first = body[0] if body else None
    if (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return body[1:]
    return body


def _local_bindings(func: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, str]:
    """Map each name the function binds to a positional placeholder.

    Parameters, assignment targets, loop and ``with`` targets, exception
    names, imports and nested definitions are local; the placeholder is the
    order of first binding, so two copies that differ only in local names
    normalize alike. Free names (globals, builtins, called functions) keep
    their identity: two functions that call different collaborators are not
    copies of each other.
    """
    bound: list[str] = []
    args = func.args
    for a in (*args.posonlyargs, *args.args, args.vararg, *args.kwonlyargs, args.kwarg):
        if a is not None:
            bound.append(a.arg)
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.append(node.id)
        elif isinstance(node, ast.arg):
            bound.append(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.append(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            bound.extend((a.asname or a.name).split(".")[0] for a in node.names)
        elif node is not func and isinstance(
            node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            bound.append(node.name)
    placeholders: dict[str, str] = {}
    for name in bound:
        placeholders.setdefault(name, f"_v{len(placeholders)}")
    return placeholders


class _LocalRenamer(ast.NodeTransformer):
    """Rename local bindings to their placeholders; leave free names alone."""

    def __init__(self, placeholders: dict[str, str]) -> None:
        self._placeholders = placeholders

    def _rename(self, name: str) -> str:
        return self._placeholders.get(name, name)

    def visit_Name(self, node: ast.Name) -> ast.Name:
        node.id = self._rename(node.id)
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = self._rename(node.arg)
        node.annotation = None
        return node

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.ExceptHandler:
        self.generic_visit(node)
        if node.name:
            node.name = self._rename(node.name)
        return node

    def visit_alias(self, node: ast.alias) -> ast.alias:
        node.asname = self._rename(node.asname or node.name)
        return node

    def _visit_def(self, node: ast.AST) -> ast.AST:
        self.generic_visit(node)
        node.name = self._rename(node.name)  # type: ignore[attr-defined]
        return node

    visit_FunctionDef = _visit_def
    visit_AsyncFunctionDef = _visit_def
    visit_ClassDef = _visit_def


def _fingerprint(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Normalized structure of ``func``, or None when its body is below the floor."""
    body = _strip_docstring(func.body)
    size = sum(
        1 for stmt in body for node in ast.walk(stmt) if not isinstance(node, ast.expr_context)
    )
    if size < _MIN_BODY_NODES:
        return None
    renamer = _LocalRenamer(_local_bindings(func))
    shape = [renamer.visit(copy.deepcopy(func.args))]
    shape.extend(renamer.visit(copy.deepcopy(stmt)) for stmt in body)
    return "|".join(ast.dump(node) for node in shape)


def _top_level_functions(
    tree: ast.Module,
) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Module functions and class methods (at any class depth), qualified by class.

    Functions nested inside another function are not collected: they are
    compared as part of their enclosing function's body.
    """
    found: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    pending: list[tuple[str, list[ast.stmt]]] = [("", tree.body)]
    while pending:
        prefix, body = pending.pop()
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append((prefix + node.name, node))
            elif isinstance(node, ast.ClassDef):
                pending.append((f"{prefix}{node.name}.", node.body))
    return found


class DuplicatedCode(Rule):
    """SMELL-002: Functions with identical normalized structure.

    Every function and method outside test files is fingerprinted after
    dropping its docstring and renaming its local bindings by order of first
    use, so copies that were edited only in their docstrings or local names
    still match. Fingerprints are compared across the whole project, not
    within one file: the commonest copy is a helper pasted into a sibling
    module. Each copy after the first (in path order) is reported at its own
    definition, naming the first, so deleting a copy lowers the count by one.

    Not reported: bodies under ``_MIN_BODY_NODES`` AST nodes, functions that
    differ in a free name they call or read, functions nested inside other
    functions, and test files (whose local helpers are duplicated on purpose).

    Principles: #2 (One concept, one home).
    Source: FOWLER Ch. 3 — Duplicated Code.
    """

    code = "SMELL-002"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Function '{function}' duplicates '{original}' ({location})"
    recommendation_template = (
        "Extract the shared logic into a single function parameterized by the differences."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        first_copy: dict[str, tuple[str, str, int]] = {}
        for f in sorted(context.files, key=lambda fi: fi.relative_path):
            if is_test_path(f.relative_path):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            functions = _top_level_functions(tree)
            for qualname, func in sorted(functions, key=lambda item: item[1].lineno):
                fingerprint = _fingerprint(func)
                if fingerprint is None:
                    continue
                original = first_copy.setdefault(
                    fingerprint, (qualname, f.relative_path, func.lineno)
                )
                if original[1:] == (f.relative_path, func.lineno):
                    continue
                findings.append(
                    self.finding(
                        file=f.relative_path,
                        line=func.lineno,
                        function=qualname,
                        original=original[0],
                        location=f"{original[1]}:{original[2]}",
                    )
                )
        return findings


# ---------------------------------------------------------------
# Exported rule instances
# ---------------------------------------------------------------

CHANGE_PREVENTER_RULES = (
    DivergentChange(),
    ShotgunSurgery(),
    DuplicatedCode(),
)
