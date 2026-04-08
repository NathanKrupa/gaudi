# ABOUTME: Django data-flow / domain rules: business logic in serializers,
# ABOUTME: signals, models, and HTTP calls inside transaction.atomic boundaries.
from __future__ import annotations

import ast

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_HTTP_CLIENT_MODULES = frozenset({"requests", "httpx", "urllib3"})
_HTTP_CLIENT_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "request", "send"}
)
_EXTERNAL_SIDE_EFFECTS = frozenset({"send_mail", "send_task", "delay", "apply_async"})


def _attr_root(node: ast.expr) -> str | None:
    """Walk an Attribute chain to its root Name and return the name."""
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _is_http_call(call: ast.Call) -> bool:
    """Return True for requests.post / httpx.get / session.request / etc."""
    func = call.func
    if isinstance(func, ast.Attribute):
        if func.attr not in _HTTP_CLIENT_METHODS:
            return False
        root = _attr_root(func.value)
        if root in _HTTP_CLIENT_MODULES:
            return True
    return False


def _is_external_side_effect(call: ast.Call) -> bool:
    """Return True for known fire-and-forget side effects (mail, celery)."""
    func = call.func
    name: str | None = None
    if isinstance(func, ast.Name):
        name = func.id
    elif isinstance(func, ast.Attribute):
        name = func.attr
    return name in _EXTERNAL_SIDE_EFFECTS


# ---------------------------------------------------------------------------
# DJ-ARCH-001  BusinessLogicInSerializer
# ---------------------------------------------------------------------------


_SERIALIZER_BASES = frozenset(
    {"Serializer", "ModelSerializer", "HyperlinkedModelSerializer", "ListSerializer"}
)
_SERIALIZER_METHODS = frozenset({"create", "update"})
_SERIALIZER_BODY_THRESHOLD = 8  # statements; thin delegations are 1-3


def _inherits_serializer(cls: ast.ClassDef) -> bool:
    for base in cls.bases:
        if isinstance(base, ast.Name) and base.id in _SERIALIZER_BASES:
            return True
        if isinstance(base, ast.Attribute) and base.attr in _SERIALIZER_BASES:
            return True
    return False


def _serializer_methods(
    cls: ast.ClassDef,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Yield create()/update() methods defined directly on a serializer class."""
    return [
        item
        for item in cls.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and item.name in _SERIALIZER_METHODS
    ]


def _count_real_statements(body: list[ast.stmt]) -> int:
    """Count statements, ignoring docstrings and bare pass."""
    n = 0
    for i, stmt in enumerate(body):
        if (
            i == 0
            and isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue
        if isinstance(stmt, ast.Pass):
            continue
        n += 1
    return n


class BusinessLogicInSerializer(Rule):
    """Detect DRF serializer create()/update() carrying domain logic.

    Principles: #2 (Surface area reflects power), #14 (Tests describe contracts).
    Source: Two Scoops of Django -- serializers convert shapes, services do work.
    """

    code = "DJ-ARCH-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "drf"
    message_template = (
        "{class_name}.{method} has {count} statements at line {line}"
        " -- move domain logic to a service"
    )
    recommendation_template = (
        "Serializers convert between wire format and domain objects. Orchestration"
        " (pricing, fulfilment, notifications) belongs in a service callable from"
        " the view, not inside create()/update()."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for cls in ast.walk(tree):
                if not isinstance(cls, ast.ClassDef) or not _inherits_serializer(cls):
                    continue
                for item in _serializer_methods(cls):
                    count = _count_real_statements(item.body)
                    if count < _SERIALIZER_BODY_THRESHOLD:
                        continue
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=item.lineno,
                            class_name=cls.name,
                            method=item.name,
                            count=count,
                        )
                    )
        return findings


# ---------------------------------------------------------------------------
# DJ-ARCH-002  BusinessLogicInSignal
# ---------------------------------------------------------------------------


_SIGNAL_NAMES = frozenset({"post_save", "pre_save", "post_delete", "pre_delete", "m2m_changed"})
_SIGNAL_COMPLEXITY_THRESHOLD = 3  # if-branches + external calls


def _is_receiver_decorator(dec: ast.expr) -> bool:
    """Return True for @receiver(post_save, ...) and similar."""
    if not isinstance(dec, ast.Call):
        return False
    func = dec.func
    name = func.id if isinstance(func, ast.Name) else (
        func.attr if isinstance(func, ast.Attribute) else None
    )
    if name != "receiver":
        return False
    if not dec.args:
        return False
    first = dec.args[0]
    first_name = first.id if isinstance(first, ast.Name) else (
        first.attr if isinstance(first, ast.Attribute) else None
    )
    return first_name in _SIGNAL_NAMES


def _signal_complexity(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Score = if-branches + outbound side-effect calls inside the handler."""
    score = 0
    for child in ast.walk(fn):
        if isinstance(child, ast.If):
            score += 1
        elif isinstance(child, ast.Call) and (
            _is_http_call(child) or _is_external_side_effect(child)
        ):
            score += 1
    return score


class BusinessLogicInSignal(Rule):
    """Detect Django signal handlers with non-trivial orchestration.

    Principles: #5 (State must be visible), #10 (Boundaries are real or fictional).
    Source: Two Scoops of Django -- signals are notification, not orchestration.
    """

    code = "DJ-ARCH-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "django"
    message_template = (
        "Signal handler '{function}' has complex orchestration at line {line}"
        " -- move work to a service"
    )
    recommendation_template = (
        "Signals are best for notification, not workflow. A handler that branches,"
        " sends mail, and calls external services hides causality. Have the view"
        " call a service explicitly instead."
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
                if not any(_is_receiver_decorator(d) for d in node.decorator_list):
                    continue
                if _signal_complexity(node) >= _SIGNAL_COMPLEXITY_THRESHOLD:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                            function=node.name,
                        )
                    )
        return findings


# ---------------------------------------------------------------------------
# DJ-ARCH-003  ModelCallsExternalService
# ---------------------------------------------------------------------------


_DJANGO_MODEL_BASES = frozenset({"Model"})


def _inherits_django_model(cls: ast.ClassDef) -> bool:
    for base in cls.bases:
        if isinstance(base, ast.Attribute) and base.attr in _DJANGO_MODEL_BASES:
            return True
        if isinstance(base, ast.Name) and base.id == "Model":
            return True
    return False


def _calls_external_service(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for child in ast.walk(fn):
        if isinstance(child, ast.Call) and (
            _is_http_call(child) or _is_external_side_effect(child)
        ):
            return True
    return False


class ModelCallsExternalService(Rule):
    """Detect Django model methods that talk to external systems.

    Principles: #2 (Surface area reflects power), #10 (Boundaries are real or fictional).
    Source: ARCH90 layer model -- inner-layer code (models) cannot reach outward.
    """

    code = "DJ-ARCH-003"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "django"
    message_template = (
        "{class_name}.{method} calls external service at line {line}"
        " -- mixes persistence with side effects"
    )
    recommendation_template = (
        "A model method may compute or persist its own state, but it must not"
        " call mail / HTTP / task queues. Move the side effect to a service that"
        " orchestrates the model and the external call."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for cls in ast.walk(tree):
                if not isinstance(cls, ast.ClassDef) or not _inherits_django_model(cls):
                    continue
                for item in cls.body:
                    if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if _calls_external_service(item):
                        findings.append(
                            self.finding(
                                file=fi.relative_path,
                                line=item.lineno,
                                class_name=cls.name,
                                method=item.name,
                            )
                        )
        return findings


# ---------------------------------------------------------------------------
# DJ-ARCH-004  TransactionBoundaryViolation
# ---------------------------------------------------------------------------


def _is_atomic_decorator(dec: ast.expr) -> bool:
    """Return True for @transaction.atomic or @transaction.atomic()."""
    target = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(target, ast.Attribute) and target.attr == "atomic":
        root = _attr_root(target.value)
        return root == "transaction"
    return False


def _is_atomic_with(item: ast.withitem) -> bool:
    """Return True for `with transaction.atomic():`."""
    ctx = item.context_expr
    target = ctx.func if isinstance(ctx, ast.Call) else ctx
    if isinstance(target, ast.Attribute) and target.attr == "atomic":
        root = _attr_root(target.value)
        return root == "transaction"
    return False


class TransactionBoundaryViolation(Rule):
    """Detect HTTP calls inside @transaction.atomic blocks.

    Principles: #11 (Bounded resources), #5 (State must be visible).
    Source: Django docs -- network I/O inside a DB transaction holds locks.
    """

    code = "DJ-ARCH-004"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    requires_library = "django"
    message_template = "{call} inside transaction.atomic at line {line} -- move outside"
    recommendation_template = (
        "Network I/O inside an atomic block holds row/table locks for the duration"
        " of the request. Commit the transaction first, then make the call -- or"
        " use on_commit() if the call must follow a successful commit."
    )

    def _http_calls(self, body: list[ast.stmt]) -> list[ast.Call]:
        out: list[ast.Call] = []
        for stmt in body:
            for child in ast.walk(stmt):
                if isinstance(child, ast.Call) and _is_http_call(child):
                    out.append(child)
        return out

    def _describe_call(self, call: ast.Call) -> str:
        func = call.func
        if isinstance(func, ast.Attribute):
            root = _attr_root(func.value) or "?"
            return f"{root}.{func.attr}"
        return "http call"

    def _atomic_bodies(self, tree: ast.Module) -> list[list[ast.stmt]]:
        """Return statement bodies that execute inside a transaction.atomic boundary."""
        bodies: list[list[ast.stmt]] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                _is_atomic_decorator(d) for d in node.decorator_list
            ):
                bodies.append(node.body)
            elif isinstance(node, (ast.With, ast.AsyncWith)) and any(
                _is_atomic_with(item) for item in node.items
            ):
                bodies.append(node.body)
        return bodies

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for body in self._atomic_bodies(tree):
                for call in self._http_calls(body):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=call.lineno,
                            call=self._describe_call(call),
                        )
                    )
        return findings


DJ_ARCH_RULES = (
    BusinessLogicInSerializer(),
    BusinessLogicInSignal(),
    ModelCallsExternalService(),
    TransactionBoundaryViolation(),
)
