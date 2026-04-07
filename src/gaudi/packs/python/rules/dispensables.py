# ABOUTME: Fowler "dispensables" code smells: things that could be removed without loss.
# ABOUTME: Lazy elements, speculative generality, excess comments, data class smell.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# Dunder method sets shared with couplers.py.
# _BOILERPLATE_DUNDERS is the base; _DATA_DUNDERS extends it.
_BOILERPLATE_DUNDERS = frozenset({"__init__", "__repr__", "__str__", "__eq__", "__hash__"})


# ---------------------------------------------------------------
# SMELL-014  LazyElement
# ---------------------------------------------------------------


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
# Exported rule instances
# ---------------------------------------------------------------

DISPENSABLE_RULES = (
    LazyElement(),
    SpeculativeGenerality(),
    Comments(),
    DataClassSmell(),
)
