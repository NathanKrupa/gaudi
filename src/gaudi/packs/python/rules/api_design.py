# ABOUTME: API design rules covering pagination, return-type consistency,
# ABOUTME: leaking integer IDs, and missing error response schemas on routes.
from __future__ import annotations

import ast
import re

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import PythonContext

_ROUTE_METHODS = frozenset({"get", "post", "put", "patch", "delete", "api_route", "route"})


def _is_route_decorator(node: ast.expr) -> bool:
    """Return True for FastAPI/Flask style @something.get/post/... decorators."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return isinstance(func, ast.Attribute) and func.attr in _ROUTE_METHODS


def _route_decorated_functions(
    tree: ast.Module,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    out: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any(_is_route_decorator(d) for d in node.decorator_list):
            out.append(node)
    return out


# ---------------------------------------------------------------
# API-001  MissingPagination
# A list endpoint that returns an unbounded queryset will eventually time out
# or OOM. Pagination is not optional for any collection that grows.
# ---------------------------------------------------------------


_TERMINAL_QUERY_METHODS = frozenset({"all", "filter"})


def _terminal_query_method(call: ast.Call) -> str | None:
    """Return 'all'/'filter' if this Call ends in .all()/.filter(), else None."""
    if isinstance(call.func, ast.Attribute) and call.func.attr in _TERMINAL_QUERY_METHODS:
        return call.func.attr
    return None


class MissingPagination(Rule):
    """Detect API list endpoints returning unbounded querysets.

    Principles: #5 (State must be visible), #11 (Bounded resources).
    Source: REST API best practices -- list endpoints must paginate.
    """

    code = "API-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = (
        "List endpoint '{function}' returns unbounded queryset (.{method}()) at line {line}"
    )
    recommendation_template = (
        "Slice the queryset (e.g. queryset[offset:offset+limit]), wrap it in a Paginator,"
        " or use a framework pagination class. Unbounded list endpoints are a latency"
        " and memory time bomb."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for fn in _route_decorated_functions(tree):
                for stmt in ast.walk(fn):
                    if not isinstance(stmt, ast.Return) or stmt.value is None:
                        continue
                    val = stmt.value
                    if not isinstance(val, ast.Call):
                        continue
                    method = _terminal_query_method(val)
                    if method is None:
                        continue
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=stmt.lineno,
                            function=fn.name,
                            method=method,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# API-002  InconsistentReturnType
# An endpoint that returns a dict in one branch and a Response object in
# another exposes two contradictory contracts. Pick one shape.
# ---------------------------------------------------------------


def _classify_return(value: ast.expr | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, ast.Dict):
        return "dict"
    if isinstance(value, ast.Call):
        func = value.func
        name: str | None = None
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        if name and "Response" in name:
            return "response"
        return "call"
    if isinstance(value, ast.Tuple):
        return "tuple"
    return "other"


def _direct_returns(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
) -> list[ast.Return]:
    """Return statements belonging to *this* function (skip nested defs)."""
    returns: list[ast.Return] = []

    def visit(node: ast.AST) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                continue
            if isinstance(child, ast.Return):
                returns.append(child)
            visit(child)

    visit(fn)
    return returns


class InconsistentReturnType(Rule):
    """Detect endpoints that mix dict literals with Response objects.

    Principles: #3 (Names are contracts), #10 (Boundaries are real or fictional).
    Source: REST API best practices -- one endpoint, one response shape.
    """

    code = "API-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = (
        "Endpoint '{function}' mixes dict literal with Response object at line {line}"
    )
    recommendation_template = (
        "Pick one return shape per endpoint -- either always return a dict (and let the"
        " framework serialize) or always return a Response object. Mixed shapes confuse"
        " clients and OpenAPI generators."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for fn in _route_decorated_functions(tree):
                returns = _direct_returns(fn)
                kinds = {_classify_return(r.value) for r in returns}
                kinds.discard(None)
                if "dict" in kinds and "response" in kinds:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=fn.lineno,
                            function=fn.name,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# API-003  LeakingInternalID
# Exposing the auto-increment integer PK in URLs leaks row counts and enables
# enumeration / BOLA attacks. Use UUIDs or slugs.
# ---------------------------------------------------------------


_DJANGO_URL_FUNCS = frozenset({"path", "re_path", "url"})
_INT_PK_RE = re.compile(r"<int:(?:pk|id|[a-zA-Z_][a-zA-Z0-9_]*_id)>")


class LeakingInternalID(Rule):
    """Detect URL patterns that expose auto-increment integer PKs.

    Principles: #10 (Boundaries are real or fictional).
    Source: OWASP API Security -- BOLA via sequential IDs.
    """

    code = "API-003"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = "URL pattern exposes <int:pk> at line {line} -- prefer UUID or slug"
    recommendation_template = (
        "Replace <int:pk> with <uuid:pk> or a slug. Sequential integer IDs leak row counts"
        " and enable BOLA-style enumeration attacks."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name: str | None = None
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name not in _DJANGO_URL_FUNCS:
                    continue
                if not node.args:
                    continue
                first = node.args[0]
                if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
                    continue
                if _INT_PK_RE.search(first.value):
                    findings.append(self.finding(file=fi.relative_path, line=node.lineno))
        return findings


# ---------------------------------------------------------------
# API-004  NoErrorResponseSchema
# A FastAPI route that declares response_model but no error responses ships an
# OpenAPI document that lies: the 4xx/5xx shape is undocumented.
# ---------------------------------------------------------------


class NoErrorResponseSchema(Rule):
    """Detect FastAPI routes with response_model but no documented error responses.

    Principles: #3 (Names are contracts).
    Source: OpenAPI specification -- error responses are part of the contract.
    """

    code = "API-004"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = (
        "Route at line {line} has response_model but no 'responses' kwarg for error codes"
    )
    recommendation_template = (
        "Add a responses={{404: {{'model': Error}}, ...}} kwarg so the OpenAPI document"
        " describes both the success and error shapes."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            if not fi.has_import("fastapi"):
                continue
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for dec in node.decorator_list:
                    if not _is_route_decorator(dec):
                        continue
                    kwargs = {kw.arg for kw in dec.keywords}
                    if "response_model" in kwargs and "responses" not in kwargs:
                        findings.append(self.finding(file=fi.relative_path, line=dec.lineno))
        return findings


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

API_DESIGN_RULES = (
    MissingPagination(),
    InconsistentReturnType(),
    LeakingInternalID(),
    NoErrorResponseSchema(),
)
