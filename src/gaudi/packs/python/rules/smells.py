"""
ABOUTME: Fowler's code smells detected via AST analysis.
ABOUTME: Tier 1 rules use basic AST node counting and pattern matching.
"""

from __future__ import annotations

import ast
from typing import Any

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


def _parse_safe(source: str) -> ast.Module | None:
    """Parse source, returning None on SyntaxError."""
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


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
            tree = _parse_safe(f.source)
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
            tree = _parse_safe(f.source)
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
            tree = _parse_safe(f.source)
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
            tree = _parse_safe(f.source)
            if tree is None:
                continue
            for node in tree.body:
                if not isinstance(node, ast.Assign):
                    continue
                value = node.value
                # Skip constant assignments
                if _is_constant_value(value):
                    continue
                # Check ALL_CAPS with constant value
                is_allcaps = all(
                    isinstance(t, ast.Name) and _is_all_caps(t.id) for t in node.targets
                )
                if is_allcaps and _is_constant_value(value):
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
            tree = _parse_safe(f.source)
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

_DUNDER_METHODS = frozenset(
    {
        "__init__",
        "__repr__",
        "__str__",
        "__eq__",
        "__hash__",
    }
)


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
            tree = _parse_safe(f.source)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                real = [m for m in methods if m.name not in _DUNDER_METHODS]
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
            tree = _parse_safe(f.source)
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
            tree = _parse_safe(f.source)
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

_DATA_DUNDERS = frozenset(
    {
        "__init__",
        "__repr__",
        "__str__",
        "__eq__",
        "__hash__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
    }
)


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
            tree = _parse_safe(f.source)
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
            tree = _parse_safe(f.source)
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
            tree = _parse_safe(f.source)
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
# Exported rule instances
# ---------------------------------------------------------------

SMELL_RULES = [
    MysteriousName(),
    LongFunction(),
    LongParameterList(),
    GlobalData(),
    Loops(),
    LazyElement(),
    MessageChains(),
    LargeClass(),
    DataClassSmell(),
    RefusedBequest(),
    Comments(),
]
