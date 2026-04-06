"""
ABOUTME: Fowler's code smells detected via AST analysis.
ABOUTME: Tier 1 rules use basic AST node counting and pattern matching.
"""

from __future__ import annotations

import ast
import copy
import itertools
from typing import Any

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
    """SMELL-001: Functions or classes that use too many mysterious names."""

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
# SMELL-003  LongFunction
# ---------------------------------------------------------------


class LongFunction(Rule):
    """SMELL-003: Functions that exceed 25 lines."""

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
    """SMELL-004: Functions with too many parameters."""

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
    """SMELL-005: Mutable module-level variables."""

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
    """SMELL-013: Accumulation loops replaceable by comprehensions."""

    code = "SMELL-013"
    severity = Severity.INFO
    category = Category.CODE_SMELL
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
# SMELL-014  LazyElement
# ---------------------------------------------------------------

# Dunder method sets used by multiple rules.
# _BOILERPLATE_DUNDERS is the base; others extend it.
_BOILERPLATE_DUNDERS = frozenset({"__init__", "__repr__", "__str__", "__eq__", "__hash__"})


class LazyElement(Rule):
    """SMELL-014: Classes with a single trivial method."""

    code = "SMELL-014"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    message_template = "Class '{class_name}' has only one method — consider inlining"
    recommendation_template = (
        "A class with a single method that just returns is "
        "likely overengineered. Use a function instead."
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
                real = [m for m in methods if m.name not in _BOILERPLATE_DUNDERS]
                if len(real) != 1:
                    continue
                body = real[0].body
                if len(body) == 1 and isinstance(body[0], ast.Return):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-017  MessageChains
# ---------------------------------------------------------------


class MessageChains(Rule):
    """SMELL-017: Long attribute access chains."""

    code = "SMELL-017"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    message_template = "Attribute chain of depth {depth} at line {line}"
    recommendation_template = (
        "Long attribute chains couple the caller to the "
        "navigation structure. Consider introducing a "
        "helper method."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            # Track nodes we've already counted as inner
            seen: set[int] = set()
            for node in ast.walk(tree):
                if not isinstance(node, ast.Attribute):
                    continue
                if id(node) in seen:
                    continue
                depth = self._chain_depth(node, seen)
                if depth >= 5:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            depth=depth,
                        )
                    )
        return findings

    def _chain_depth(self, node: ast.Attribute, seen: set[int]) -> int:
        """Count nested Attribute depth, marking inner nodes."""
        depth = 1
        current = node.value
        while isinstance(current, ast.Attribute):
            seen.add(id(current))
            depth += 1
            current = current.value
        return depth


# ---------------------------------------------------------------
# SMELL-020  LargeClass
# ---------------------------------------------------------------


class LargeClass(Rule):
    """SMELL-020: Classes with too many methods or attributes."""

    code = "SMELL-020"
    severity = Severity.WARN
    category = Category.CODE_SMELL
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
# SMELL-022  DataClassSmell
# ---------------------------------------------------------------

_DATA_DUNDERS = _BOILERPLATE_DUNDERS | {"__lt__", "__le__", "__gt__", "__ge__"}


class DataClassSmell(Rule):
    """SMELL-022: Classes that are pure data holders."""

    code = "SMELL-022"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    message_template = "Class '{class_name}' is a pure data holder — consider using a dataclass"
    recommendation_template = (
        "Use @dataclass or a NamedTuple for pure data "
        "containers. They provide __init__, __repr__, and "
        "__eq__ automatically."
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
                if not methods:
                    continue
                has_init = any(m.name == "__init__" for m in methods)
                if not has_init:
                    continue
                all_data = all(m.name in _DATA_DUNDERS for m in methods)
                if all_data:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
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
# SMELL-024  Comments
# ---------------------------------------------------------------


class Comments(Rule):
    """SMELL-024: Functions with excessive comment density."""

    code = "SMELL-024"
    severity = Severity.INFO
    category = Category.CODE_SMELL
    message_template = (
        "Function '{function}' has {comment_count} comments in {code_count} lines of code"
    )
    recommendation_template = (
        "High comment density suggests the code should be "
        "clearer. Rename variables and extract methods "
        "instead of adding comments."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            source_lines = f.source.splitlines()
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.end_lineno is None:
                    continue
                # Include preceding comment block
                start = node.lineno - 1
                while start > 0 and source_lines[start - 1].strip().startswith("#"):
                    start -= 1
                end = node.end_lineno
                func_lines = source_lines[start:end]
                comment_count = 0
                code_count = 0
                for line in func_lines:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    if stripped.startswith("#"):
                        comment_count += 1
                    else:
                        code_count += 1
                if (
                    comment_count >= 5
                    and code_count > 0
                    and comment_count / (comment_count + code_count) > 0.5
                ):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            function=node.name,
                            comment_count=comment_count,
                            code_count=code_count,
                        )
                    )
        return findings


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
    """SMELL-006: Shared mutable state mutated by multiple functions."""

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


class DivergentChange(Rule):
    """SMELL-007: Class methods touch disjoint attribute sets."""

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
                non_init = [m for m in methods if m.name != "__init__"]
                attr_sets = [_method_attr_set(m) for m in non_init]
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
# SMELL-009  FeatureEnvy
# ---------------------------------------------------------------


class FeatureEnvy(Rule):
    """SMELL-009: Method accesses another object more than its own."""

    code = "SMELL-009"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = (
        "Method '{method}' in '{class_name}' accesses another object's attributes more than its own"
    )
    recommendation_template = "Move this method to the class it's most interested in."

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for cls in ast.walk(tree):
                if not isinstance(cls, ast.ClassDef):
                    continue
                for method in cls.body:
                    if not isinstance(method, ast.FunctionDef):
                        continue
                    params = {a.arg for a in method.args.args if a.arg not in ("self", "cls")}
                    if not params:
                        continue
                    self_count = 0
                    other_count = 0
                    for node in ast.walk(method):
                        if not isinstance(node, ast.Attribute):
                            continue
                        if not isinstance(node.value, ast.Name):
                            continue
                        if node.value.id == "self":
                            self_count += 1
                        elif node.value.id in params:
                            other_count += 1
                    if other_count >= 4 and other_count > 2 * self_count:
                        findings.append(
                            self.finding(
                                file=f.relative_path,
                                line=method.lineno,
                                method=method.name,
                                class_name=cls.name,
                            )
                        )
        return findings


# ---------------------------------------------------------------
# SMELL-010  DataClumps
# ---------------------------------------------------------------


class DataClumps(Rule):
    """SMELL-010: Same parameter groups in multiple functions."""

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
    """SMELL-011: Attribute compared to many string literals."""

    code = "SMELL-011"
    severity = Severity.WARN
    category = Category.CODE_SMELL
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
# SMELL-015  SpeculativeGenerality
# ---------------------------------------------------------------


class SpeculativeGenerality(Rule):
    """SMELL-015: Premature abstractions or unused parameters."""

    code = "SMELL-015"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "{detail}"
    recommendation_template = "{advice}"

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            findings.extend(self._check_abstract(tree, f.relative_path))
            findings.extend(self._check_unused_params(tree, f.relative_path))
        return findings

    def _check_abstract(
        self,
        tree: ast.Module,
        path: str,
    ) -> list[Finding]:
        results: list[Finding] = []
        # Find abstract classes and their subclasses
        classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        abc_classes: set[str] = set()
        for cls in classes:
            for node in ast.walk(cls):
                if isinstance(node, ast.Name):
                    if node.id in ("abstractmethod", "ABC"):
                        abc_classes.add(cls.name)
                        break
                if isinstance(node, ast.Attribute):
                    if node.attr == "abstractmethod":
                        abc_classes.add(cls.name)
                        break
        # Count subclasses per abstract class
        for abc_name in abc_classes:
            subs = sum(
                1
                for cls in classes
                if cls.name != abc_name
                and any((isinstance(b, ast.Name) and b.id == abc_name) for b in cls.bases)
            )
            if subs <= 1:
                results.append(
                    self.finding(
                        file=path,
                        line=1,
                        detail=f"Abstract class '{abc_name}' has only {subs} subclass",
                        advice="If there's only one implementation, the abstraction is premature.",
                        class_name=abc_name,
                        count=subs,
                    )
                )
        return results

    def _check_unused_params(
        self,
        tree: ast.Module,
        path: str,
    ) -> list[Finding]:
        results: list[Finding] = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            # Find params with default None
            args = node.args
            defaults = list(args.defaults)
            # Pad defaults to align with args
            num_no_default = len(args.args) - len(defaults)
            padded = [None] * num_no_default + defaults
            none_params: list[str] = []
            for arg, default in zip(args.args, padded):
                if arg.arg in ("self", "cls"):
                    continue
                if (
                    default is not None
                    and isinstance(default, ast.Constant)
                    and default.value is None
                ):
                    none_params.append(arg.arg)
            # Also check kwonlyargs
            for arg, default in zip(args.kwonlyargs, args.kw_defaults):
                if (
                    default is not None
                    and isinstance(default, ast.Constant)
                    and default.value is None
                ):
                    none_params.append(arg.arg)
            if len(none_params) < 2:
                continue
            # Check which are unused in body
            body_names: set[str] = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Name):
                    body_names.add(child.id)
            unused = [p for p in none_params if p not in body_names]
            if len(unused) >= 2:
                results.append(
                    self.finding(
                        file=path,
                        line=node.lineno,
                        detail=(
                            f"Function '{node.name}' has "
                            f"{len(unused)} unused parameters: "
                            f"{', '.join(unused)}"
                        ),
                        advice="Remove unused parameters. They add complexity without value.",
                        function=node.name,
                        count=len(unused),
                        params=", ".join(unused),
                    )
                )
        return results


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
# SMELL-018  MiddleMan
# ---------------------------------------------------------------

_DUNDER_SKIP = _BOILERPLATE_DUNDERS | {"__len__", "__bool__", "__enter__", "__exit__", "__del__"}


def _is_pure_delegation(method: ast.FunctionDef) -> bool:
    """Check if method body is just return self._x.y(...)."""
    body = method.body
    if len(body) != 1:
        return False
    stmt = body[0]
    if not isinstance(stmt, ast.Return):
        return False
    val = stmt.value
    if not isinstance(val, ast.Call):
        return False
    func = val.func
    if not isinstance(func, ast.Attribute):
        return False
    obj = func.value
    if not isinstance(obj, ast.Attribute):
        return False
    if not isinstance(obj.value, ast.Name):
        return False
    if obj.value.id != "self":
        return False
    return True


class MiddleMan(Rule):
    """SMELL-018: Class that mostly delegates to another."""

    code = "SMELL-018"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = (
        "Class '{class_name}' delegates {delegated}/{total} methods — it's a middle man"
    )
    recommendation_template = (
        "If a class mostly delegates, remove it and use the underlying object directly."
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
                methods = [
                    m
                    for m in node.body
                    if isinstance(m, ast.FunctionDef) and m.name not in _DUNDER_SKIP
                ]
                if len(methods) < 3:
                    continue
                delegated = sum(1 for m in methods if _is_pure_delegation(m))
                total = len(methods)
                if delegated > total / 2 and delegated >= 2:
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            class_name=node.name,
                            delegated=delegated,
                            total=total,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SMELL-019  InsiderTrading
# ---------------------------------------------------------------


class InsiderTrading(Rule):
    """SMELL-019: Method writes to another object's attributes."""

    code = "SMELL-019"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = (
        "Method '{method}' in '{class_name}' directly modifies {count} attributes of other objects"
    )
    recommendation_template = (
        "Ask objects to modify themselves instead of reaching into their internals."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for cls in ast.walk(tree):
                if not isinstance(cls, ast.ClassDef):
                    continue
                for method in cls.body:
                    if not isinstance(method, ast.FunctionDef):
                        continue
                    params = {a.arg for a in method.args.args if a.arg not in ("self", "cls")}
                    if not params:
                        continue
                    writes = 0
                    for node in ast.walk(method):
                        targets: list[ast.expr] = []
                        if isinstance(node, ast.Assign):
                            targets = list(node.targets)
                        elif isinstance(node, ast.AugAssign):
                            targets = [node.target]
                        for t in targets:
                            if (
                                isinstance(t, ast.Attribute)
                                and isinstance(t.value, ast.Name)
                                and t.value.id in params
                            ):
                                writes += 1
                    if writes >= 2:
                        findings.append(
                            self.finding(
                                file=f.relative_path,
                                line=method.lineno,
                                method=method.name,
                                class_name=cls.name,
                                count=writes,
                            )
                        )
        return findings


# ---------------------------------------------------------------
# SMELL-002  DuplicatedCode
# ---------------------------------------------------------------


class _Normalizer(ast.NodeTransformer):
    """Replace all names with placeholders for comparison."""

    def visit_Name(self, node: ast.Name) -> ast.Name:
        node.id = "VAR"
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = "ARG"
        return node


class DuplicatedCode(Rule):
    """SMELL-002: Functions with identical normalized structure."""

    code = "SMELL-002"
    severity = Severity.WARN
    category = Category.CODE_SMELL
    message_template = "Functions '{func1}' and '{func2}' have duplicate structure"
    recommendation_template = (
        "Extract the shared logic into a single function parameterized by the differences."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            # Normalize and dump each function
            dumps: list[tuple[str, str]] = []
            for fn in funcs:
                fn_copy = copy.deepcopy(fn)
                fn_copy.name = "FUNC"
                _Normalizer().visit(fn_copy)
                dumps.append((fn.name, ast.dump(fn_copy)))
            seen_pairs: set[frozenset[str]] = set()
            for i in range(len(dumps)):
                for j in range(i + 1, len(dumps)):
                    if dumps[i][1] == dumps[j][1]:
                        pair = frozenset({dumps[i][0], dumps[j][0]})
                        if pair not in seen_pairs:
                            seen_pairs.add(pair)
                            names = sorted(pair)
                            findings.append(
                                self.finding(
                                    file=f.relative_path,
                                    line=1,
                                    func1=names[0],
                                    func2=names[1],
                                )
                            )
        return findings


# ---------------------------------------------------------------
# SMELL-008  ShotgunSurgery
# ---------------------------------------------------------------


class ShotgunSurgery(Rule):
    """SMELL-008: Module-level name used in 4+ functions."""

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

SMELL_RULES = (
    MysteriousName(),
    DuplicatedCode(),
    LongFunction(),
    LongParameterList(),
    GlobalData(),
    MutableData(),
    DivergentChange(),
    ShotgunSurgery(),
    FeatureEnvy(),
    DataClumps(),
    PrimitiveObsession(),
    RepeatedSwitches(),
    Loops(),
    LazyElement(),
    SpeculativeGenerality(),
    TemporaryField(),
    MessageChains(),
    MiddleMan(),
    InsiderTrading(),
    LargeClass(),
    AlternativeInterfaces(),
    DataClassSmell(),
    RefusedBequest(),
    Comments(),
)
