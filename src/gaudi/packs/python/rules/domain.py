"""
ABOUTME: Domain model rules from Fowler's Patterns of Enterprise Application Architecture.
ABOUTME: DOM-001 AnemicDomainModel, DOM-002 WrongLayerPlacement, DOM-003 ActiveRecordMisuse.
"""

from __future__ import annotations

import ast

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# DOM-001  AnemicDomainModel
# ---------------------------------------------------------------

_ANEMIC_FIELD_THRESHOLD = 5

_DOMAIN_BASE_HINTS = frozenset(
    {
        "Model",  # Django: models.Model
        "BaseModel",  # Pydantic
        "Base",  # SQLAlchemy declarative
        "DeclarativeBase",  # SQLAlchemy 2.x
    }
)

_NON_BEHAVIOR_DUNDERS = frozenset(
    {
        "__init__",
        "__post_init__",
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


def _inherits_domain_base(cls: ast.ClassDef) -> bool:
    for base in cls.bases:
        if isinstance(base, ast.Attribute) and base.attr in _DOMAIN_BASE_HINTS:
            return True
        if isinstance(base, ast.Name) and base.id in _DOMAIN_BASE_HINTS:
            return True
    return False


def _is_django_field(value: ast.expr) -> bool:
    """A `something.SomethingField(...)` or `models.X(...)` call."""
    if not isinstance(value, ast.Call):
        return False
    func = value.func
    if isinstance(func, ast.Attribute):
        return True
    if isinstance(func, ast.Name) and func.id.endswith("Field"):
        return True
    return False


def _count_django_fields(cls: ast.ClassDef) -> int:
    count = 0
    for node in cls.body:
        if isinstance(node, ast.Assign) and _is_django_field(node.value):
            count += sum(1 for t in node.targets if isinstance(t, ast.Name))
    return count


def _count_pydantic_fields(cls: ast.ClassDef) -> int:
    """An annotated assignment at class level is a Pydantic / SQLAlchemy 2.x field."""
    return sum(1 for node in cls.body if isinstance(node, ast.AnnAssign))


def _count_behavior_methods(cls: ast.ClassDef) -> int:
    count = 0
    for node in cls.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name in _NON_BEHAVIOR_DUNDERS:
            continue
        count += 1
    return count


class AnemicDomainModel(Rule):
    """DOM-001: Domain model with many fields and zero behavior.

    A class that inherits a known domain base (Django ``models.Model``,
    Pydantic ``BaseModel``, SQLAlchemy declarative ``Base``) with at least
    five fields and zero behavior methods is a pure data bag where the
    domain logic must live elsewhere. Plain ``@dataclass`` records are out
    of scope — see SMELL-022 for the general data-class smell.

    Principles: #1 (The structure tells the story), #9 (Dependencies flow
    toward stability — domain models should be the most-depended-upon code
    and therefore the place behavior lives).
    Source: FOWLER PEAA — Anemic Domain Model.
    """

    code = "DOM-001"
    severity = Severity.WARN
    category = Category.DOMAIN_MODEL
    # Fowler's DDD-era critique of data-without-behavior. Functional,
    # Data-Oriented, Event-Sourced, Unix, and Pragmatic all use
    # anemic records deliberately — frozen dataclasses, parallel
    # arrays, events. See docs/philosophy/functional.md catechism #1.
    philosophy_scope = frozenset({"classical", "convention"})
    message_template = (
        "Domain model '{class_name}' has {field_count} fields and zero "
        "behavior methods — anemic data bag"
    )
    recommendation_template = (
        "Move the business rules that operate on this data into methods on "
        "the model itself. A model that only holds fields forces logic to "
        "scatter across services and views."
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
                if not _inherits_domain_base(node):
                    continue
                # Django: assignments to *Field(...) calls.
                # Pydantic / SQLAlchemy 2.x: annotated assignments.
                field_count = max(
                    _count_django_fields(node),
                    _count_pydantic_fields(node),
                )
                if field_count < _ANEMIC_FIELD_THRESHOLD:
                    continue
                if _count_behavior_methods(node) > 0:
                    continue
                findings.append(
                    self.finding(
                        file=f.relative_path,
                        line=node.lineno,
                        class_name=node.name,
                        field_count=field_count,
                    )
                )
        return findings


# ---------------------------------------------------------------
# DOM-002  WrongLayerPlacement
# ---------------------------------------------------------------

_BRANCH_THRESHOLD = 4  # >3 branches per the spec


def _is_view_file(relative_path: str) -> bool:
    norm = relative_path.replace("\\", "/")
    if norm.endswith("/views.py") or norm == "views.py":
        return True
    return "/views/" in norm or norm.startswith("views/")


def _count_branches(node: ast.If) -> int:
    """Count branches in an if/elif chain rooted at ``node``."""
    count = 1
    current = node
    while len(current.orelse) == 1 and isinstance(current.orelse[0], ast.If):
        count += 1
        current = current.orelse[0]
    return count


def _walk_branched_ifs(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Return the largest if/elif branch count anywhere in the function body."""
    largest = 0
    seen_inner: set[int] = set()
    # First pass: collect ids of If nodes that are the orelse-child of another If
    # so we don't double-count an elif as the start of a new chain.
    for node in ast.walk(func):
        if (
            isinstance(node, ast.If)
            and len(node.orelse) == 1
            and isinstance(node.orelse[0], ast.If)
        ):
            seen_inner.add(id(node.orelse[0]))
    for node in ast.walk(func):
        if isinstance(node, ast.If) and id(node) not in seen_inner:
            largest = max(largest, _count_branches(node))
    return largest


class WrongLayerPlacement(Rule):
    """DOM-002: Business logic living inside view/endpoint functions.

    Detects long if/elif chains in functions that live in view files. View
    code should translate between HTTP and the service layer; branching
    business decisions belong in services.

    Principles: #1 (The structure tells the story — outer layer parses input
    and formats output, middle layer makes decisions), #7 (Layers must earn
    their existence — a view that contains business rules collapses two
    layers into one).
    Source: FOWLER PEAA — Service Layer, Domain Logic in the Wrong Place.
    """

    code = "DOM-002"
    severity = Severity.WARN
    category = Category.DOMAIN_MODEL
    message_template = (
        "View function '{function}' contains a {branch_count}-branch "
        "if/elif chain — business logic in the outer layer"
    )
    recommendation_template = (
        "Move the branching decision into a service or model method and "
        "have the view delegate to it. Views should parse input and format "
        "output, not decide policy."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            if not _is_view_file(f.relative_path):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                branches = _walk_branched_ifs(node)
                if branches < _BRANCH_THRESHOLD:
                    continue
                findings.append(
                    self.finding(
                        file=f.relative_path,
                        line=node.lineno,
                        function=node.name,
                        branch_count=branches,
                    )
                )
        return findings


# ---------------------------------------------------------------
# DOM-003  ActiveRecordMisuse
# ---------------------------------------------------------------

_EXTERNAL_CALL_NAMES = frozenset(
    {
        "send_mail",
        "send_mass_mail",
    }
)

_EXTERNAL_CALL_ATTRS = frozenset(
    {
        "post",
        "get",
        "put",
        "patch",
        "delete",
        "request",
        "send_task",
        "apply_async",
        "publish",
    }
)

_EXTERNAL_CALL_MODULES = frozenset(
    {
        "requests",
        "httpx",
        "urllib",
        "celery",
        "boto3",
        "smtplib",
    }
)


def _call_is_external(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Name) and func.id in _EXTERNAL_CALL_NAMES:
        return True
    if isinstance(func, ast.Attribute):
        # requests.post(...), httpx.get(...), celery_app.send_task(...)
        if isinstance(func.value, ast.Name) and func.value.id in _EXTERNAL_CALL_MODULES:
            return True
        if (
            func.attr in _EXTERNAL_CALL_ATTRS
            and isinstance(func.value, ast.Name)
            and func.value.id not in {"self", "cls"}
        ):
            return True
    return False


class ActiveRecordMisuse(Rule):
    """DOM-003: Model class methods that call external services directly.

    A persistence model that fires HTTP requests, sends email, or pushes
    onto a task queue is mixing two concerns: storing data and orchestrating
    side effects. The Active Record pattern handles persistence; orchestration
    belongs in a service.

    Principles: #10 (Boundaries are real or fictional — a model that also
    talks to an external system has collapsed the boundary between
    persistence and orchestration).
    Source: FOWLER PEAA — Active Record, Service Layer.
    """

    code = "DOM-003"
    severity = Severity.INFO
    category = Category.DOMAIN_MODEL
    message_template = (
        "Model method '{class_name}.{method}' calls an external service "
        "directly — move orchestration into a service"
    )
    recommendation_template = (
        "Extract the external call into a service that takes the model as "
        "input. Persistence and orchestration are separate responsibilities."
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
                if not _inherits_domain_base(node):
                    continue
                for member in node.body:
                    if not isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    for sub in ast.walk(member):
                        if isinstance(sub, ast.Call) and _call_is_external(sub):
                            findings.append(
                                self.finding(
                                    file=f.relative_path,
                                    line=member.lineno,
                                    class_name=node.name,
                                    method=member.name,
                                )
                            )
                            break
        return findings


# ---------------------------------------------------------------
# Exported rule instances
# ---------------------------------------------------------------

DOMAIN_RULES = (
    AnemicDomainModel(),
    WrongLayerPlacement(),
    ActiveRecordMisuse(),
)
