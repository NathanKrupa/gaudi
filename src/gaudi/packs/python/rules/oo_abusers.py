# ABOUTME: Fowler "object-orientation abusers" code smells: misuse of OO mechanisms.
# ABOUTME: Refused bequest, alternative interfaces, repeated switches, temporary fields.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# SMELL-012  RepeatedSwitches
# ---------------------------------------------------------------


def _extract_switch_pattern(
    node: ast.If,
) -> tuple[str | None, frozenset[str]]:
    """
    Extract (variable_name, {literal_values}) from an if/elif chain.
    Returns (None, empty) if not a string-literal switch.
    """
    var_name: str | None = None
    values: set[str] = set()

    current: ast.stmt | None = node
    while current is not None and isinstance(current, ast.If):
        test = current.test
        cmp_var, cmp_val = _extract_compare(test)
        if cmp_var is None:
            break
        if var_name is None:
            var_name = cmp_var
        elif cmp_var != var_name:
            break
        values.add(cmp_val)
        # Follow elif chain
        if current.orelse and len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
            current = current.orelse[0]
        else:
            break
    if var_name and len(values) >= 2:
        return var_name, frozenset(values)
    return None, frozenset()


def _extract_compare(
    test: ast.expr,
) -> tuple[str | None, str | None]:
    """Extract (var_name, string_value) from a comparison."""
    if not isinstance(test, ast.Compare):
        return None, None
    if len(test.ops) != 1:
        return None, None
    if not isinstance(test.ops[0], ast.Eq):
        return None, None
    left = test.left
    right = test.comparators[0]
    var_node = None
    str_node = None
    if isinstance(left, ast.Name) and isinstance(right, ast.Constant):
        var_node = left
        str_node = right
    elif isinstance(right, ast.Name) and isinstance(left, ast.Constant):
        var_node = right
        str_node = left
    if var_node is None or str_node is None or not isinstance(str_node.value, str):
        return None, None
    return var_node.id, str_node.value


class RepeatedSwitches(Rule):
    """SMELL-012: Same switch pattern in multiple functions."""

    code = "SMELL-012"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Switch on values ({values}) repeated in {count} functions"
    recommendation_template = (
        "Replace repeated switches with polymorphism or a dispatch dictionary."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            # Collect switch patterns per function
            patterns: dict[frozenset[str], list[str]] = {}
            for node in ast.walk(tree):
                if not isinstance(
                    node,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    continue
                for child in ast.walk(node):
                    if not isinstance(child, ast.If):
                        continue
                    _, vals = _extract_switch_pattern(child)
                    if len(vals) >= 2:
                        patterns.setdefault(vals, [])
                        fn = node.name
                        if fn not in patterns[vals]:
                            patterns[vals].append(fn)
                        break
            for vals, funcs in patterns.items():
                if len(funcs) >= 2:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=1,
                            values=", ".join(sorted(vals)),
                            count=len(funcs),
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-016  TemporaryField
# ---------------------------------------------------------------


class TemporaryField(Rule):
    """SMELL-016: Class with attributes set in only one method."""

    code = "SMELL-016"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Class '{class_name}' has {count} temporary fields: {fields}"
    recommendation_template = (
        "Temporary fields suggest the class has multiple "
        "responsibilities. Extract into separate classes "
        "or use method-local variables."
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
                init_attrs: set[str] = set()
                method_attrs: dict[str, set[str]] = {}
                for m in node.body:
                    if not isinstance(m, ast.FunctionDef):
                        continue
                    attrs: set[str] = set()
                    for child in ast.walk(m):
                        if not isinstance(child, ast.Assign):
                            continue
                        for t in child.targets:
                            if (
                                isinstance(t, ast.Attribute)
                                and isinstance(t.value, ast.Name)
                                and t.value.id == "self"
                            ):
                                attrs.add(t.attr)
                    if m.name == "__init__":
                        init_attrs = attrs
                    else:
                        method_attrs[m.name] = attrs
                # Temporary: set in exactly 1 non-init
                # method and NOT in __init__
                all_non_init: dict[str, int] = {}
                for attrs in method_attrs.values():
                    for a in attrs:
                        all_non_init[a] = all_non_init.get(a, 0) + 1
                temp = [a for a, cnt in all_non_init.items() if cnt == 1 and a not in init_attrs]
                if len(temp) >= 2:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
                            count=len(temp),
                            fields=", ".join(sorted(temp)),
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-023  RefusedBequest
# ---------------------------------------------------------------

_IGNORED_BASES = frozenset({"object", "ABC"})


def _is_refused_body(body: list[ast.stmt]) -> bool:
    """Check if a method body is pass, Ellipsis, or raise."""
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Pass):
        return True
    if (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and stmt.value.value is ...
    ):
        return True
    if isinstance(stmt, ast.Raise):
        exc = stmt.exc
        if exc is None:
            return True
        if isinstance(exc, ast.Call):
            func = exc.func
            if isinstance(func, ast.Name) and func.id == "NotImplementedError":
                return True
        if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
            return True
    return False


class RefusedBequest(Rule):
    """SMELL-023: Subclasses that refuse inherited behavior."""

    code = "SMELL-023"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Class '{class_name}' refuses {count} of {total} inherited methods"
    recommendation_template = (
        "If a subclass doesn't want parent behavior, prefer composition over inheritance."
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
                bases = [
                    b
                    for b in node.bases
                    if not (isinstance(b, ast.Name) and b.id in _IGNORED_BASES)
                ]
                if not bases:
                    continue
                methods = [
                    n for n in node.body if isinstance(n, ast.FunctionDef) and n.name != "__init__"
                ]
                if len(methods) < 2:
                    continue
                refused = sum(1 for m in methods if _is_refused_body(m.body))
                if refused >= 2 and refused >= len(methods) / 2:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
                            count=refused,
                            total=len(methods),
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-021  AlternativeInterfaces
# ---------------------------------------------------------------


class AlternativeInterfaces(Rule):
    """SMELL-021: Similar classes with different method names."""

    code = "SMELL-021"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    message_template = (
        "{count} classes have similar structure but different method names: {classes}"
    )
    recommendation_template = "Define a common Protocol or ABC to unify the interface."

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            # Filter: no inheritance (or just object)
            plain: list[ast.ClassDef] = []
            for cls in classes:
                bases = [b for b in cls.bases if not (isinstance(b, ast.Name) and b.id == "object")]
                if not bases:
                    plain.append(cls)
            if len(plain) < 3:
                continue
            # Build signature: (method_count, param_counts)
            sigs: dict[tuple[int, tuple[int, ...]], list[str]] = {}
            for cls in plain:
                methods = [
                    m
                    for m in cls.body
                    if isinstance(m, ast.FunctionDef) and not m.name.startswith("__")
                ]
                if not methods:
                    continue
                param_counts = tuple(
                    sorted(len([a for a in m.args.args if a.arg != "self"]) for m in methods)
                )
                sig = (len(methods), param_counts)
                sigs.setdefault(sig, [])
                # Only add if method names differ
                # from existing entries
                sigs[sig].append(cls.name)
            for sig, names in sigs.items():
                if len(names) < 3:
                    continue
                # Check that method names differ
                method_sets: list[frozenset[str]] = []
                for cls in plain:
                    if cls.name not in names:
                        continue
                    ms = frozenset(
                        m.name
                        for m in cls.body
                        if isinstance(m, ast.FunctionDef) and not m.name.startswith("__")
                    )
                    method_sets.append(ms)
                # At least 2 must have different names
                if len(set(method_sets)) >= 2:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=1,
                            count=len(names),
                            classes=", ".join(sorted(names)),
                        )
                    )
        return findings


# ---------------------------------------------------------------
# Exported rule instances
# ---------------------------------------------------------------

OO_ABUSER_RULES = (
    RepeatedSwitches(),
    TemporaryField(),
    RefusedBequest(),
    AlternativeInterfaces(),
)
