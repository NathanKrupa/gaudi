# ABOUTME: SQLAlchemy-specific architectural rules for Gaudi Python pack.
# ABOUTME: Covers default lazy loading (N+1 prevention) via AST analysis.
from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.ast_helpers import describe_call, is_http_client_call
from gaudi.packs.python.context import PythonContext


class SQLAlchemyLazyDefault(Rule):
    """Detect SQLAlchemy relationships without explicit lazy loading strategy.

    Principles: #4 (Failure must be named).
    Source: FWDOCS SQLAlchemy — default lazy loading causes N+1 failures under load.
    """

    code = "SA-SCALE-001"
    severity = Severity.WARN
    category = Category.SCALABILITY
    requires_library = "sqlalchemy"
    message_template = "relationship() using default lazy loading at line {line}"
    recommendation_template = (
        "Explicitly set lazy='select', 'joined', 'subquery', or 'selectin' on relationships. "
        "Default lazy loading causes N+1 queries."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                is_relationship = (isinstance(func, ast.Name) and func.id == "relationship") or (
                    isinstance(func, ast.Attribute) and func.attr == "relationship"
                )
                if not is_relationship:
                    continue
                if not any(kw.arg == "lazy" for kw in node.keywords):
                    findings.append(self.finding(file=f.relative_path, line=node.lineno))
        return findings


# ---------------------------------------------------------------------------
# SA-ARCH-001  TransactionBoundaryIO
# ---------------------------------------------------------------------------

# Context managers that open a database transaction. `begin` and `begin_nested`
# are SQLAlchemy (Session, Engine, Connection); `transaction` is psycopg 3's
# equivalent. Matching is on the method name alone — see the class docstring
# for why the scope stops there.
_TRANSACTION_CONTEXT_METHODS = frozenset({"begin", "begin_nested", "transaction"})


def _opens_a_transaction(item: ast.withitem) -> bool:
    """True for `with session.begin():`, `with engine.begin() as conn:`, etc."""
    ctx = item.context_expr
    target = ctx.func if isinstance(ctx, ast.Call) else ctx
    return isinstance(target, ast.Attribute) and target.attr in _TRANSACTION_CONTEXT_METHODS


class TransactionBoundaryIO(Rule):
    """Detect a network call inside a SQLAlchemy/psycopg transaction block.

    Principles: #4 (Failure must be named), #11 (Bounded resources).
    Source: Nygard, *Release It!* — a remote call inside a transaction couples
    the lifetime of a database lock to a third party's availability.

    DJ-ARCH-004 asks this question of Django's ``transaction.atomic()``. A repo
    on SQLAlchemy has no such call site, so it was asked of nothing: grantspider
    has 0 ``atomic()`` blocks and 43 explicit ``.commit()`` calls, and both of
    its transaction incidents (a four-day CRASHED service, 357 rows of paid
    model output lost) were structurally invisible.

    **Scope is deliberately shallow.** Only the body of a ``with`` block whose
    context manager is a ``.begin()`` / ``.begin_nested()`` / ``.transaction()``
    call is examined, and only for calls whose receiver root is a known HTTP
    client module. A transaction opened without a ``with`` block, or a session
    bound through a helper, is not tracked — dataflow analysis here would buy a
    handful of extra findings at the price of false positives on ordinary code,
    and a rule that fires on ordinary code gets disabled repo-wide.
    """

    code = "SA-ARCH-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    requires_library = "sqlalchemy"
    message_template = "{call} at line {line} runs inside a database transaction"
    recommendation_template = (
        "A network call inside a transaction holds its locks for as long as the"
        " remote host takes to answer — and a hung request holds them until the"
        " connection times out. Fetch before opening the transaction, or commit"
        " first and do the call afterwards."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.With, ast.AsyncWith)):
                    continue
                if not any(_opens_a_transaction(item) for item in node.items):
                    continue
                for stmt in node.body:
                    for child in ast.walk(stmt):
                        if isinstance(child, ast.Call) and is_http_client_call(child):
                            findings.append(
                                self.finding(
                                    file=fi.relative_path,
                                    line=child.lineno,
                                    call=describe_call(child),
                                )
                            )
        return findings


SQLALCHEMY_RULES = (
    SQLAlchemyLazyDefault(),
    TransactionBoundaryIO(),
)
