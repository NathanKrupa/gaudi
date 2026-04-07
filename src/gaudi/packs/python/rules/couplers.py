# ABOUTME: Fowler "couplers" code smells: classes that know too much about each other.
# ABOUTME: Feature envy, message chains, middle man, insider trading.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext
from gaudi.packs.python.rules.dispensables import _BOILERPLATE_DUNDERS


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
# Exported rule instances
# ---------------------------------------------------------------

COUPLER_RULES = (
    FeatureEnvy(),
    MessageChains(),
    MiddleMan(),
    InsiderTrading(),
)
