"""
ABOUTME: Fowler code smells that don't fit the other sub-category modules.
ABOUTME: Mysterious names, global data, accumulation loops, mutable shared state.
"""

from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# SMELL-001  MysteriousName
# ---------------------------------------------------------------

_GENERIC_NAMES = frozenset(
    {
        "data",
        "temp",
        "val",
        "obj",
        "result",
        "stuff",
        "d",
        "x",
    }
)
_LOOP_VARS_OK = frozenset({"i", "j", "k"})


def _for_target_names(node: ast.For) -> set[str]:
    """Collect all Name ids from a for-loop target."""
    names: set[str] = set()
    if isinstance(node.target, ast.Name):
        names.add(node.target.id)
    elif isinstance(node.target, ast.Tuple):
        for elt in node.target.elts:
            if isinstance(elt, ast.Name):
                names.add(elt.id)
    return names


def _mysterious_in_function(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[str]:
    """Return mysterious local-variable names in a function body."""
    loop_targets: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.For):
            loop_targets |= _for_target_names(node)

    mysterious: list[str] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                if name == "_":
                    continue
                if len(name) == 1 and name not in _LOOP_VARS_OK | loop_targets:
                    mysterious.append(name)
                elif name in _GENERIC_NAMES:
                    mysterious.append(name)
    return mysterious


def _mysterious_in_init(cls: ast.ClassDef) -> list[str]:
    """Return mysterious self.x attribute names in __init__."""
    mysterious: list[str] = []
    for node in cls.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name != "__init__":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Assign):
                continue
            for target in child.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    attr = target.attr
                    if attr == "_":
                        continue
                    if len(attr) == 1 or attr in _GENERIC_NAMES:
                        mysterious.append(f"self.{attr}")
    return mysterious


class MysteriousName(Rule):
    """SMELL-001: Functions or classes that use too many mysterious names.

    Principles: #3 (Names are contracts), #11 (The reader is the user).
    Source: FOWLER Ch. 3 — Mysterious Name.
    """

    code = "SMELL-001"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    message_template = "Function '{function}' uses {count} mysterious names: {names}"
    recommendation_template = (
        "Use descriptive names that reveal intent. Single-letter variables obscure meaning."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names = _mysterious_in_function(node)
                    if len(names) >= 3:
                        findings.append(
                            self.finding(
                                file=f.relative_path,
                                line=node.lineno,
                                function=node.name,
                                count=len(names),
                                names=", ".join(sorted(set(names))),
                            )
                        )
                elif isinstance(node, ast.ClassDef):
                    names = _mysterious_in_init(node)
                    if len(names) >= 3:
                        findings.append(
                            self.finding(
                                file=f.relative_path,
                                line=node.lineno,
                                function=f"{node.name}.__init__",
                                count=len(names),
                                names=", ".join(sorted(set(names))),
                            )
                        )
        return findings


# ---------------------------------------------------------------
# SMELL-005  GlobalData
# ---------------------------------------------------------------


def _is_all_caps(name: str) -> bool:
    return name == name.upper() and name.isidentifier()


def _is_constant_value(node: ast.expr) -> bool:
    """Return True if the node is a safe constant."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.Tuple):
        return all(_is_constant_value(e) for e in node.elts)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return isinstance(node.operand, ast.Constant)
    return False


def _is_reference_data(node: ast.expr) -> bool:
    """Return True if node is a non-empty dict/list used as reference data."""
    if isinstance(node, ast.Dict):
        if not node.keys:
            return False
        return all(k is not None for k in node.keys)
    if isinstance(node, ast.List):
        return bool(node.elts)
    return False


def _is_mutable_call(node: ast.expr) -> bool:
    """Check if a Call creates a mutable container."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id in ("dict", "list", "set"):
        return True
    return False


class GlobalData(Rule):
    """SMELL-005: Mutable module-level variables.

    Principles: #5 (State must be visible).
    Source: FOWLER Ch. 3 — Global Data.
    """

    code = "SMELL-005"
    severity = Severity.ERROR
    category = Category.CODE_SMELL
    message_template = "Module-level mutable variable '{name}' at line {line}"
    recommendation_template = (
        "Avoid mutable module-level variables. Use function-local "
        "state, dependency injection, or frozen data structures."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                value = node.value
                # Skip constant assignments
                if _is_constant_value(value):
                    continue
                # Skip dunder names (__all__, __version__, etc.)
                if any(
                    isinstance(t, ast.Name) and t.id.startswith("__") and t.id.endswith("__")
                    for t in node.targets
                ):
                    continue
                # ALL_CAPS with immutable value = constant
                is_allcaps = all(
                    isinstance(t, ast.Name) and _is_all_caps(t.id) for t in node.targets
                )
                if is_allcaps and _is_constant_value(value):
                    continue
                # ALL_CAPS tuple = constant (rule registries)
                if is_allcaps and isinstance(value, ast.Tuple):
                    continue
                # ALL_CAPS non-empty dict/list = reference data table
                if is_allcaps and _is_reference_data(value):
                    continue
                # Flag mutable containers
                is_mutable = isinstance(value, (ast.Dict, ast.List, ast.Set)) or _is_mutable_call(
                    value
                )
                if not is_mutable:
                    continue
                for target in node.targets:
                    name = target.id if isinstance(target, ast.Name) else ast.dump(target)
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            name=name,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-013  Loops
# ---------------------------------------------------------------


def _is_append_on(call: ast.Call, var_name: str) -> bool:
    """Check if call is var_name.append(...)."""
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "append"
        and isinstance(func.value, ast.Name)
        and func.value.id == var_name
    )


class Loops(Rule):
    """SMELL-013: Accumulation loops replaceable by comprehensions.

    Principles: #11 (The reader is the user).
    Source: FOWLER Ch. 3 — Loops.
    """

    code = "SMELL-013"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    # Scoped away from Data-Oriented: comprehensions allocate
    # intermediate collections; manual fused loops are cache-coherent.
    # See docs/philosophy/data-oriented.md catechism #6.
    philosophy_scope = frozenset(
        {
            "classical",
            "pragmatic",
            "functional",
            "unix",
            "resilient",
            "convention",
            "event-sourced",
        }
    )
    message_template = "Loop at line {line} could be replaced with a comprehension or builtin"
    recommendation_template = (
        "Use a list comprehension, generator expression, or sum() instead of an accumulation loop."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    findings.extend(self._scan_stmts(node.body, f.relative_path))
        return findings

    def _scan_stmts(self, stmts: list[ast.stmt], filepath: str) -> list[Finding]:
        results: list[Finding] = []
        for i, stmt in enumerate(stmts):
            if not isinstance(stmt, ast.Assign):
                continue
            if len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if not isinstance(target, ast.Name):
                continue
            var = target.id
            value = stmt.value
            next_stmt = stmts[i + 1] if i + 1 < len(stmts) else None
            if next_stmt is None or not isinstance(next_stmt, ast.For):
                continue

            # Pattern 1: x = [], for ... : x.append(...)
            if isinstance(value, ast.List) and len(value.elts) == 0:
                body = next_stmt.body
                if self._is_append_body(body, var):
                    results.append(
                        self.finding(
                            file=filepath,
                            line=next_stmt.lineno,
                        )
                    )
                    continue

            # Pattern 2: x = 0, for ... : x += ...
            if isinstance(value, ast.Constant) and value.value in (0, 0.0):
                body = next_stmt.body
                if (
                    len(body) == 1
                    and isinstance(body[0], ast.AugAssign)
                    and isinstance(body[0].op, ast.Add)
                    and isinstance(body[0].target, ast.Name)
                    and body[0].target.id == var
                ):
                    results.append(
                        self.finding(
                            file=filepath,
                            line=next_stmt.lineno,
                        )
                    )
        return results

    def _is_append_body(self, body: list[ast.stmt], var: str) -> bool:
        """Check if body is a single append or if-guarded append."""
        if len(body) != 1:
            return False
        stmt = body[0]
        # Direct append
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and _is_append_on(stmt.value, var)
        ):
            return True
        # If-guarded append
        if isinstance(stmt, ast.If):
            return self._is_append_body(stmt.body, var)
        return False


# ---------------------------------------------------------------
# SMELL-006  MutableData
# ---------------------------------------------------------------

_MUTATING_METHODS = frozenset(
    {
        "append",
        "extend",
        "insert",
        "remove",
        "pop",
        "clear",
        "update",
        "add",
        "discard",
        "setdefault",
        "sort",
        "reverse",
    }
)


def _find_module_mutable_names(tree: ast.Module) -> dict[str, int]:
    """Return {name: lineno} for module-level mutable assignments."""
    names: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        val = node.value
        is_mutable = isinstance(val, (ast.Dict, ast.List, ast.Set)) or _is_mutable_call(val)
        if not is_mutable:
            continue
        for t in node.targets:
            if isinstance(t, ast.Name):
                names[t.id] = node.lineno
    return names


def _function_mutates(
    func: ast.FunctionDef,
    name: str,
) -> bool:
    """Check if function mutates the given module-level variable."""
    for node in ast.walk(func):
        # Subscript assign: name[x] = ...
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (
                    isinstance(t, ast.Subscript)
                    and isinstance(t.value, ast.Name)
                    and t.value.id == name
                ):
                    return True
        # Augmented assign: name += ...
        if isinstance(node, ast.AugAssign):
            t = node.target
            if isinstance(t, ast.Name) and t.id == name:
                return True
            if (
                isinstance(t, ast.Subscript)
                and isinstance(t.value, ast.Name)
                and t.value.id == name
            ):
                return True
        # Method calls: name.append(...), etc.
        if isinstance(node, ast.Call):
            func_attr = node.func
            if (
                isinstance(func_attr, ast.Attribute)
                and isinstance(func_attr.value, ast.Name)
                and func_attr.value.id == name
                and func_attr.attr in _MUTATING_METHODS
            ):
                return True
    return False


class MutableData(Rule):
    """SMELL-006: Shared mutable state mutated by multiple functions.

    Principles: #5 (State must be visible).
    Source: FOWLER Ch. 3 — Mutable Data.
    """

    code = "SMELL-006"
    severity = Severity.ERROR
    category = Category.CODE_SMELL
    message_template = "Function '{function}' mutates shared state '{name}' at line {line}"
    recommendation_template = (
        "Avoid shared mutable state. Pass data as function parameters and return results."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            mutables = _find_module_mutable_names(tree)
            if not mutables:
                continue
            funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            for name, lineno in mutables.items():
                mutators = [fn for fn in funcs if _function_mutates(fn, name)]
                if len(mutators) >= 2:
                    for fn in mutators:
                        findings.append(
                            self.finding(
                                file=f.relative_path,
                                line=lineno,
                                function=fn.name,
                                name=name,
                            )
                        )
        return findings


# ---------------------------------------------------------------
# Exported rule instances
# ---------------------------------------------------------------

SMELL_RULES = (
    MysteriousName(),
    GlobalData(),
    Loops(),
    MutableData(),
)
