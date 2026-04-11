# ABOUTME: Fowler "bloaters" code smells: things that grow until they hurt.
# ABOUTME: Long functions, parameter lists, large classes, primitive obsession, data clumps.
from __future__ import annotations

import ast
import itertools
from typing import Any

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# SMELL-003  LongFunction
# ---------------------------------------------------------------


class LongFunction(Rule):
    """SMELL-003: Functions that exceed 25 lines.

    Principles: #7 (Layers must earn their existence), #11 (The reader is the user).
    Source: FOWLER Ch. 3 — Long Function.
    """

    code = "SMELL-003"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Function '{function}' is {lines} lines long"
    recommendation_template = (
        "Extract smaller functions. Long functions are hard to understand, test, and reuse."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.end_lineno is None:
                    continue
                lines = node.end_lineno - node.lineno + 1
                if lines > 25:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            function=node.name,
                            lines=lines,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-004  LongParameterList
# ---------------------------------------------------------------


class LongParameterList(Rule):
    """SMELL-004: Functions with too many parameters.

    Principles: #11 (The reader is the user), #3 (Names are contracts).
    Source: FOWLER Ch. 3 — Long Parameter List.
    """

    code = "SMELL-004"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Function '{function}' has {count} parameters"
    recommendation_template = (
        "Introduce a parameter object or split the function. "
        "Long parameter lists are hard to understand."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                args = node.args
                params = [a for a in args.args + args.kwonlyargs if a.arg not in ("self", "cls")]
                count = len(params)

                # Count boolean defaults
                all_defaults = list(args.defaults) + list(args.kw_defaults)
                bool_defaults = sum(
                    1
                    for d in all_defaults
                    if isinstance(d, ast.Constant) and isinstance(d.value, bool)
                )

                if count > 6 or bool_defaults >= 3:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            function=node.name,
                            count=count,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-020  LargeClass
# ---------------------------------------------------------------


class LargeClass(Rule):
    """SMELL-020: Classes with too many methods or attributes.

    Principles: #7 (Layers must earn their existence), #2 (One concept, one home).
    Source: FOWLER Ch. 3 — Large Class.
    """

    code = "SMELL-020"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    # Scoped away from Convention: fat models and fat controllers are
    # the blessed Django/Rails pattern. See docs/philosophy/convention.md.
    philosophy_scope = frozenset(
        {
            "classical",
            "pragmatic",
            "functional",
            "unix",
            "resilient",
            "data-oriented",
            "event-sourced",
        }
    )
    message_template = "Class '{class_name}' has {methods} methods and {attrs} attributes"
    recommendation_template = (
        "Large classes have too many responsibilities. "
        "Extract related methods into separate classes."
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
                method_count = len(methods)
                attr_count = self._count_init_attrs(node)
                if method_count >= 10 or (method_count + attr_count) >= 15:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
                            methods=method_count,
                            attrs=attr_count,
                        )
                    )
        return findings

    def _count_init_attrs(self, cls: ast.ClassDef) -> int:
        """Count unique self.x assignments in __init__."""
        attrs: set[str] = set()
        for node in cls.body:
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                for child in ast.walk(node):
                    if not isinstance(child, ast.Assign):
                        continue
                    for target in child.targets:
                        if (
                            isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"
                        ):
                            attrs.add(target.attr)
        return len(attrs)


# ---------------------------------------------------------------
# SMELL-010  DataClumps
# ---------------------------------------------------------------


class DataClumps(Rule):
    """SMELL-010: Same parameter groups in multiple functions.

    Principles: #2 (One concept, one home).
    Source: FOWLER Ch. 3 — Data Clumps.
    """

    code = "SMELL-010"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    message_template = "Parameters ({params}) appear together in {count} functions"
    recommendation_template = "Extract these related parameters into a dataclass or named tuple."

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            # Collect param sets for all functions
            param_sets: list[set[str]] = []
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                params = {
                    a.arg
                    for a in node.args.args + node.args.kwonlyargs
                    if a.arg not in ("self", "cls")
                }
                if len(params) >= 3:
                    param_sets.append(params)
            if len(param_sets) < 3:
                continue
            # Find groups of 3+ params in 3+ functions
            seen: set[frozenset[str]] = set()
            all_params: set[str] = set()
            for ps in param_sets:
                all_params |= ps
            # Check all 3-combinations
            for group_tuple in itertools.combinations(sorted(all_params), 3):
                group = frozenset(group_tuple)
                if group in seen:
                    continue
                count = sum(1 for ps in param_sets if group <= ps)
                if count >= 3:
                    seen.add(group)
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=1,
                            params=", ".join(sorted(group)),
                            count=count,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-011  PrimitiveObsession
# ---------------------------------------------------------------


def _collect_attr_string_compares(
    tree: ast.Module,
) -> dict[str, set[str]]:
    """
    Find attribute-to-string-literal comparisons across the file.
    Returns {attr_repr: set_of_string_values}.
    """
    result: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        # Check left == "str" or left == "str" patterns
        comparators = [node.left] + list(node.comparators)
        ops = node.ops
        for i, op in enumerate(ops):
            if not isinstance(op, (ast.Eq, ast.NotEq)):
                continue
            left = comparators[i]
            right = comparators[i + 1]
            attr_node = None
            str_node = None
            if (
                isinstance(left, ast.Attribute)
                and isinstance(right, ast.Constant)
                and isinstance(right.value, str)
            ):
                attr_node = left
                str_node = right
            elif (
                isinstance(right, ast.Attribute)
                and isinstance(left, ast.Constant)
                and isinstance(left.value, str)
            ):
                attr_node = right
                str_node = left
            if attr_node is None:
                continue
            # Build attribute representation
            parts: list[str] = []
            cur: Any = attr_node
            while isinstance(cur, ast.Attribute):
                parts.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                parts.append(cur.id)
            parts.reverse()
            attr_repr = ".".join(parts)
            result.setdefault(attr_repr, set())
            result[attr_repr].add(str_node.value)
    return result


class PrimitiveObsession(Rule):
    """SMELL-011: Attribute compared to many string literals.

    Principles: #3 (Names are contracts).
    Source: FOWLER Ch. 3 — Primitive Obsession.
    """

    code = "SMELL-011"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    # Scoped away from Unix/Data-Oriented: Unix embraces plain strings
    # at module boundaries; Data-Oriented prefers packed primitives
    # for cache locality.
    philosophy_scope = frozenset({"classical", "functional", "convention", "event-sourced"})
    message_template = "Attribute '{attr}' compared to {count} string literals — consider an enum"
    recommendation_template = (
        "Replace string comparisons with an Enum. Enums catch typos at definition time."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            compares = _collect_attr_string_compares(tree)
            for attr, values in compares.items():
                if len(values) >= 3:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=1,
                            attr=attr,
                            count=len(values),
                        )
                    )
        return findings


# ---------------------------------------------------------------
# Exported rule instances
# ---------------------------------------------------------------

BLOATER_RULES = (
    LongFunction(),
    LongParameterList(),
    LargeClass(),
    DataClumps(),
    PrimitiveObsession(),
)
