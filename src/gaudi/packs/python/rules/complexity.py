# ABOUTME: Ousterhout complexity rules from A Philosophy of Software Design.
# ABOUTME: Detects shallow modules, pass-through variables, information leakage, and conjoined methods.
from __future__ import annotations

import ast

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import PythonContext


def _public_module_members(tree: ast.Module) -> list[ast.AST]:
    """Top-level public functions and classes (or those in __all__ if present)."""
    explicit: set[str] | None = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        explicit = {
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        }

    members: list[ast.AST] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if explicit is not None:
                if node.name in explicit:
                    members.append(node)
            elif not node.name.startswith("_"):
                members.append(node)
    return members


def _body_line_span(node: ast.AST) -> int:
    """Total source-line span of a function/class body, excluding the def line itself."""
    if not hasattr(node, "body") or not node.body:
        return 0
    body = node.body  # type: ignore[attr-defined]
    # Skip a leading docstring
    if (
        isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if not body:
        return 0
    start = body[0].lineno
    end = max((getattr(stmt, "end_lineno", stmt.lineno) or stmt.lineno) for stmt in body)
    return max(0, end - start + 1)


# ---------------------------------------------------------------
# CPLX-001  ShallowModule
# Ousterhout Ch. 4: "Modules Should Be Deep"
# ---------------------------------------------------------------

_MIN_PUBLIC_MEMBERS = 5
_MAX_AVG_DEPTH = 3.0


class ShallowModule(Rule):
    code = "CPLX-001"
    severity = Severity.INFO
    category = Category.COMPLEXITY
    message_template = (
        "Module exposes {public_count} public names but averages "
        "{avg_depth:.1f} implementation lines per name -- shallow interface"
    )
    recommendation_template = (
        "Deepen the module by combining trivial helpers or hiding them behind "
        "fewer, richer entry points. Ousterhout: 'modules should be deep' -- "
        "the cost of a public name is the documentation and cognitive load it "
        "imposes on every caller."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            if fi.path.name == "__init__.py":
                continue
            tree = fi.ast_tree
            if tree is None:
                continue
            members = _public_module_members(tree)
            if len(members) < _MIN_PUBLIC_MEMBERS:
                continue
            # Skip pure data/constants modules: only count modules whose public
            # members include at least one function or class with a body.
            total_impl = sum(_body_line_span(m) for m in members)
            if total_impl == 0:
                continue
            avg_depth = total_impl / len(members)
            if avg_depth <= _MAX_AVG_DEPTH:
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=members[0].lineno,
                        public_count=len(members),
                        avg_depth=avg_depth,
                    )
                )
        return findings


# ---------------------------------------------------------------
# CPLX-002  PassThroughVariable
# Ousterhout Ch. 7: "Different Layer, Different Abstraction"
# ---------------------------------------------------------------

_PASSTHROUGH_MIN_FUNCS = 3


def _function_uses_param_only_as_passthrough(
    func: ast.FunctionDef | ast.AsyncFunctionDef, name: str
) -> bool:
    """True if every Name(load) reference to `name` inside func is as a call argument."""
    pass_through_uses = 0
    other_uses = 0
    for node in ast.walk(func):
        if node is func:
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip nested functions to avoid scope confusion
            continue
        if isinstance(node, ast.Name) and node.id == name and isinstance(node.ctx, ast.Load):
            other_uses += 1
    # Re-walk to count pass-through uses
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            for arg in node.args:
                if isinstance(arg, ast.Name) and arg.id == name:
                    pass_through_uses += 1
            for kw in node.keywords:
                if isinstance(kw.value, ast.Name) and kw.value.id == name:
                    pass_through_uses += 1
    if pass_through_uses == 0:
        return False
    # Allowed: every Name load is a call argument (other_uses == pass_through_uses)
    return other_uses == pass_through_uses


def _function_params(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = func.args
    names: list[str] = []
    for a in args.posonlyargs + args.args + args.kwonlyargs:
        if a.arg != "self" and a.arg != "cls":
            names.append(a.arg)
    if args.vararg:
        names.append(args.vararg.arg)
    if args.kwarg:
        names.append(args.kwarg.arg)
    return names


class PassThroughVariable(Rule):
    code = "CPLX-002"
    severity = Severity.WARN
    category = Category.COMPLEXITY
    message_template = (
        "Parameter '{param}' is threaded through {count} functions in this module "
        "without being used directly -- pass-through variable"
    )
    recommendation_template = (
        "Pass-through variables signal a wrong abstraction boundary. "
        "Consider grouping the threaded values into a context object, "
        "or moving the work that needs '{param}' down to the layer that already has it."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            # Map param-name -> list of (function_node) where it's pure pass-through
            passthrough: dict[str, list[ast.AST]] = {}
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for param in _function_params(node):
                    if _function_uses_param_only_as_passthrough(node, param):
                        passthrough.setdefault(param, []).append(node)
            for param, funcs in passthrough.items():
                if len(funcs) >= _PASSTHROUGH_MIN_FUNCS:
                    first = funcs[0]
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=first.lineno,
                            param=param,
                            count=len(funcs),
                        )
                    )
        return findings


# ---------------------------------------------------------------
# CPLX-003  InformationLeakage
# Ousterhout Ch. 5: "Information Hiding"
# ---------------------------------------------------------------


def _annotation_leaks_private(ann: ast.expr | None) -> str | None:
    """Return the leaked private name if the annotation references a `_`-prefixed type."""
    if ann is None:
        return None
    for node in ast.walk(ann):
        if isinstance(node, ast.Name) and node.id.startswith("_") and not node.id.startswith("__"):
            return node.id
        if isinstance(node, ast.Attribute):
            # Walk to the leftmost Name to see if it's a private module
            cur: ast.expr = node
            while isinstance(cur, ast.Attribute):
                cur = cur.value
            if isinstance(cur, ast.Name) and cur.id.startswith("_") and not cur.id.startswith("__"):
                return cur.id
    return None


class InformationLeakage(Rule):
    code = "CPLX-003"
    severity = Severity.WARN
    category = Category.COMPLEXITY
    message_template = "Public function '{func}' exposes private type '{leaked}' in its signature"
    recommendation_template = (
        "Information leakage couples callers to implementation details. "
        "Either widen '{leaked}' to a public type/protocol or make '{func}' itself private. "
        "Ousterhout: 'each module should hide information about how it works.'"
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name.startswith("_"):
                    continue
                annotations: list[ast.expr | None] = [node.returns]
                for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
                    annotations.append(a.annotation)
                for ann in annotations:
                    leaked = _annotation_leaks_private(ann)
                    if leaked:
                        findings.append(
                            self.finding(
                                file=fi.relative_path,
                                line=node.lineno,
                                func=node.name,
                                leaked=leaked,
                            )
                        )
                        break
        return findings


# ---------------------------------------------------------------
# CPLX-004  ConjoinedMethods
# Ousterhout Ch. 6: "General-Purpose Modules are Deeper"
# ---------------------------------------------------------------


def _self_attr_assigned(method: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(method):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if (
                    isinstance(tgt, ast.Attribute)
                    and isinstance(tgt.value, ast.Name)
                    and tgt.value.id == "self"
                ):
                    names.add(tgt.attr)
    return names


def _self_attr_guarded_raises(method: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return self attrs that are checked for None/falsiness and trigger a Raise."""
    guarded: set[str] = set()
    for node in ast.walk(method):
        if not isinstance(node, ast.If):
            continue
        # Check the test for `self.X is None` or `not self.X` or `self.X is None`
        attrs = _attrs_in_test(node.test)
        if not attrs:
            continue
        # Look for a Raise inside the if-body
        for child in ast.walk(node):
            if isinstance(child, ast.Raise):
                guarded.update(attrs)
                break
    return guarded


def _attrs_in_test(test: ast.expr) -> set[str]:
    attrs: set[str] = set()
    # `self.X is None`
    if isinstance(test, ast.Compare):
        if (
            isinstance(test.left, ast.Attribute)
            and isinstance(test.left.value, ast.Name)
            and test.left.value.id == "self"
        ):
            for op, comp in zip(test.ops, test.comparators):
                if isinstance(op, (ast.Is, ast.IsNot, ast.Eq, ast.NotEq)):
                    if isinstance(comp, ast.Constant) and comp.value is None:
                        attrs.add(test.left.attr)
    # `not self.X`
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        operand = test.operand
        if (
            isinstance(operand, ast.Attribute)
            and isinstance(operand.value, ast.Name)
            and operand.value.id == "self"
        ):
            attrs.add(operand.attr)
    return attrs


class ConjoinedMethods(Rule):
    code = "CPLX-004"
    severity = Severity.INFO
    category = Category.COMPLEXITY
    message_template = (
        "Class '{cls}' has temporal coupling on 'self.{attr}' between methods "
        "'{setter}' and '{checker}'"
    )
    recommendation_template = (
        "Conjoined methods force callers to remember a specific call order. "
        "Combine '{setter}' and '{checker}' into one operation, use a context manager, "
        "or pass the state explicitly so the order is impossible to get wrong."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for cls in ast.walk(tree):
                if not isinstance(cls, ast.ClassDef):
                    continue
                # Build setter map: attr -> first method that assigns it (excluding __init__)
                setters: dict[str, str] = {}
                checkers: dict[str, tuple[str, int]] = {}
                for item in cls.body:
                    if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if item.name == "__init__":
                        continue
                    for attr in _self_attr_assigned(item):
                        setters.setdefault(attr, item.name)
                    for attr in _self_attr_guarded_raises(item):
                        if attr not in checkers:
                            checkers[attr] = (item.name, item.lineno)
                for attr, (checker_name, checker_line) in checkers.items():
                    if attr in setters and setters[attr] != checker_name:
                        findings.append(
                            self.finding(
                                file=fi.relative_path,
                                line=checker_line,
                                cls=cls.name,
                                attr=attr,
                                setter=setters[attr],
                                checker=checker_name,
                            )
                        )
        return findings


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

COMPLEXITY_RULES = (
    ShallowModule(),
    PassThroughVariable(),
    InformationLeakage(),
    ConjoinedMethods(),
)
