# ABOUTME: Error handling rules for exception hygiene.
# ABOUTME: Detects bare/broad excepts, errors logged without re-raising, and lookups that hide a missing key.
from __future__ import annotations

import ast
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.ast_helpers import is_logger_call, is_test_path
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# ERR-001  BareExcept
# ---------------------------------------------------------------


class BareExcept(Rule):
    """Detect bare except blocks and broad Exception handlers.

    Principles: #4 (Failure must be named).
    Source: ARCH90 Day 5 — catch the exception you actually expect.
    """

    code = "ERR-001"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = "Broad exception handler at line {line} swallows errors"
    recommendation_template = (
        "Catch specific exceptions. If you must catch broadly, re-raise after handling."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                is_bare = node.type is None
                is_broad = isinstance(node.type, ast.Name) and node.type.id == "Exception"
                if not (is_bare or is_broad):
                    continue
                if self._body_has_raise(node.body):
                    continue
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=node.lineno,
                    )
                )
        return findings

    @staticmethod
    def _body_has_raise(body: list[ast.stmt]) -> bool:
        for child in ast.walk(ast.Module(body=body)):
            if isinstance(child, ast.Raise):
                return True
        return False


# ---------------------------------------------------------------
# ERR-003  ErrorSwallowing
# ---------------------------------------------------------------


class ErrorSwallowing(Rule):
    """Detect exceptions that are logged but not re-raised (error swallowing).

    Principles: #4 (Failure must be named), #13 (The system must explain itself).
    Source: ARCH90 Day 5 — silent failure is hidden from monitoring.

    The rule keys on the *swallow*, not on the level the handler logged at.
    A handler that logs at warning and returns a sentinel hides the failure
    exactly as thoroughly as one that logs at error — and the level is the
    author's estimate of severity, which is the thing being questioned. Keying
    on level made this rule blind to 88% of one estate repo's swallow
    population, including the one that stamped 30-day empty sentinels across
    an object-store outage.

    A handler that logs nothing is out of scope: ERR-001 (broad except without
    re-raise) and ERR-004 (`except: pass`) own that ground.
    """

    code = "ERR-003"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = "Exception logged but not re-raised at line {line}"
    recommendation_template = (
        "Logging an error without re-raising hides failures."
        " Log and re-raise, or handle the error explicitly."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                has_log = False
                has_raise = False
                for child in ast.walk(ast.Module(body=node.body)):
                    if isinstance(child, ast.Raise):
                        has_raise = True
                    if isinstance(child, ast.Call) and is_logger_call(child):
                        has_log = True
                if has_log and not has_raise:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# ERR-002  BroadTryBlock
# ---------------------------------------------------------------


class BroadTryBlock(Rule):
    """Detect try blocks wrapping more than 10 statements.

    Principles: #4 (Failure must be named).
    Source: Nygard, *Release It!* — Fail Fast. A try block over many statements
    hides which operation actually raised, so the handler can't respond
    intelligently.
    """

    code = "ERR-002"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = "try block at line {line} wraps {count} statements; narrow it"
    recommendation_template = (
        "Wrap only the operation that can fail in try. Move setup and "
        "post-processing outside the try block."
    )

    THRESHOLD = 10

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Try):
                    continue
                count = _count_statements(node.body)
                if count > self.THRESHOLD:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                            count=count,
                        )
                    )
        return findings


def _count_statements(body: list[ast.stmt]) -> int:
    """Count statements in a block, recursing into compound bodies."""
    total = 0
    for stmt in body:
        total += 1
        for field in ("body", "orelse", "finalbody"):
            inner = getattr(stmt, field, None)
            if isinstance(inner, list):
                total += _count_statements(inner)
        if isinstance(stmt, ast.Try):
            for handler in stmt.handlers:
                total += _count_statements(handler.body)
    return total


# ---------------------------------------------------------------
# ERR-004  ExceptPass
# ---------------------------------------------------------------


class ExceptPass(Rule):
    """Detect except handlers whose body is just `pass`.

    Principles: #4 (Failure must be named), #13 (The system must explain itself).
    Source: Nygard, *Release It!* — silent failure is invisible to operators.
    Distinct from ERR-001 (bare/broad except without re-raise): this fires on
    *any* except clause, however specific, that does literally nothing.
    """

    code = "ERR-004"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = "except handler at line {line} silently swallows the exception"
    recommendation_template = (
        "Log, handle, or re-raise the exception. `pass` makes failures invisible."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# ERR-005  InconsistentExceptions
# ---------------------------------------------------------------


_BUILTIN_EXC_ROOTS = frozenset({"Exception", "BaseException", "object"})


class InconsistentExceptions(Rule):
    """Flag modules that raise 4+ exception types with no shared project base.

    Principles: #4 (Failure must be named), #6 (Predictable contracts).
    Source: Nygard — callers can only handle a module's failures predictably
    if its exceptions form a coherent hierarchy.
    """

    code = "ERR-005"
    severity = Severity.INFO
    category = Category.ERROR_HANDLING
    message_template = "module raises {count} unrelated exception types with no shared base"
    recommendation_template = (
        "Define a module-level base exception (e.g. `class FooError(Exception)`) "
        "and have specific failures inherit from it so callers can catch one type."
    )

    THRESHOLD = 4

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            inheritance = _collect_inheritance(tree)
            raised: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Raise) and node.exc is not None:
                    name = _raise_type_name(node.exc)
                    if name is not None:
                        raised.add(name)
            if len(raised) < self.THRESHOLD:
                continue
            if _share_project_base(raised, inheritance):
                continue
            findings.append(
                self.finding(
                    file=fi.relative_path,
                    line=1,
                    count=len(raised),
                )
            )
        return findings


def _raise_type_name(exc: ast.expr) -> str | None:
    """Extract the exception class name from a Raise expression."""
    if isinstance(exc, ast.Call):
        exc = exc.func
    if isinstance(exc, ast.Name):
        return exc.id
    if isinstance(exc, ast.Attribute):
        return exc.attr
    return None


def _collect_inheritance(tree: ast.AST) -> dict[str, set[str]]:
    """Map each ClassDef name to the set of base names it lists in the module."""
    inheritance: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases: set[str] = set()
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.add(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.add(base.attr)
            inheritance[node.name] = bases
    return inheritance


def _ancestors(name: str, inheritance: dict[str, set[str]]) -> set[str]:
    """Return all transitive ancestors of `name` known from this module."""
    seen: set[str] = set()
    stack = [name]
    while stack:
        cur = stack.pop()
        for base in inheritance.get(cur, ()):
            if base in seen or base in _BUILTIN_EXC_ROOTS:
                continue
            seen.add(base)
            stack.append(base)
    return seen


def _share_project_base(names: set[str], inheritance: dict[str, set[str]]) -> bool:
    """True if every name in `names` resolves to at least one common project base."""
    common: set[str] | None = None
    for name in names:
        bases = _ancestors(name, inheritance)
        if not bases:
            return False
        common = bases if common is None else common & bases
        if not common:
            return False
    return bool(common)


# ---------------------------------------------------------------
# ERR-006  ExceptionInInit
# ---------------------------------------------------------------


_INIT_ALLOWED_EXCEPTIONS = frozenset({"ValueError", "TypeError"})


class ExceptionInInit(Rule):
    """Flag __init__ methods that raise non-validation exceptions or re-raise bare.

    Principles: #4 (Failure must be named).
    Source: Nygard, *Release It!* — Construct or Fail. Raising mid-construction
    leaves a partially built object whose state is undefined; exceptions about
    bad arguments (ValueError, TypeError) are the conventional exception.
    """

    code = "ERR-006"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = (
        "__init__ at line {line} raises a non-validation exception; "
        "construction can leave a partially built object"
    )
    recommendation_template = (
        "Move side effects out of __init__ into a classmethod factory, or "
        "restrict __init__ to ValueError/TypeError on bad arguments."
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
                if node.name != "__init__":
                    continue
                for child in ast.walk(node):
                    if not isinstance(child, ast.Raise):
                        continue
                    if child.exc is None:
                        findings.append(self.finding(file=fi.relative_path, line=child.lineno))
                        continue
                    name = _raise_type_name(child.exc)
                    if name is None or name in _INIT_ALLOWED_EXCEPTIONS:
                        continue
                    findings.append(self.finding(file=fi.relative_path, line=child.lineno))
        return findings


# ---------------------------------------------------------------
# ERR-007  ChainedEmptyDefaultGet
# ---------------------------------------------------------------


def _is_empty_dict(node: ast.expr) -> bool:
    if isinstance(node, ast.Dict):
        return not node.keys
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "dict"
        and not node.args
        and not node.keywords
    )


def _is_get_call(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "get"
        and bool(node.args)
    )


def _get_default(call: ast.Call) -> ast.expr | None:
    if len(call.args) >= 2:
        return call.args[1]
    for kw in call.keywords:
        if kw.arg == "default":
            return kw.value
    return None


def _empty_default_key(receiver: ast.expr) -> ast.Call | None:
    """The ``.get`` call that substitutes ``{}`` for a missing key, if ``receiver`` is one.

    Matches ``x.get(k, {})``, ``x.get(k, dict())``, ``x.get(k, default={})`` and
    ``(x.get(k) or {})``.
    """
    if _is_get_call(receiver):
        default = _get_default(receiver)  # type: ignore[arg-type]
        if default is not None and _is_empty_dict(default):
            return receiver  # type: ignore[return-value]
        return None
    if (
        isinstance(receiver, ast.BoolOp)
        and isinstance(receiver.op, ast.Or)
        and len(receiver.values) == 2
        and _is_get_call(receiver.values[0])
        and _is_empty_dict(receiver.values[1])
    ):
        return receiver.values[0]  # type: ignore[return-value]
    return None


def _has_visible_default(call: ast.Call) -> bool:
    """True when the last lookup falls back to a non-empty string the output will show."""
    default = _get_default(call)
    return (
        isinstance(default, ast.Constant) and isinstance(default.value, str) and bool(default.value)
    )


def _describe_key(call: ast.Call) -> str:
    key = call.args[0]
    if isinstance(key, ast.Constant):
        return repr(key.value)
    return ast.unparse(key)


class ChainedEmptyDefaultGet(Rule):
    """ERR-007: ``.get(key, {}).get(...)`` turns a missing key into a silent None.

    The empty-dict default exists so the next ``.get`` cannot raise, which
    means a key that is absent, renamed upstream or misspelled at the call
    site produces the same result as a key whose value is legitimately
    empty. Nothing fails and nothing logs: a whole column can read as empty
    with no signal that the lookup never matched. Also matched:
    ``(x.get(k) or {}).get(...)``, the ``dict()`` default and the ``default=``
    keyword. One finding per chain, naming the first key that was defaulted.

    A default with content (``.get(k, {"city": "unknown"})``) is a real
    fallback value, not a mask, and does not fire; nor does a chain whose last
    lookup falls back to a non-empty string (``.get("stage", "-")``), which
    the output shows. Test files are skipped: a test that reads a nested value
    goes on to assert it, so a missing key fails there.

    Principles: #4 (Failure must be named), #5 (State must be visible).
    Source: Nygard, *Release It!* — fail fast; a lookup that cannot fail cannot
    tell the caller it found nothing.
    """

    code = "ERR-007"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = (
        "Chained .get() defaults {key} to {{}}, so a missing or misspelled key "
        "reads as empty data instead of failing"
    )
    recommendation_template = (
        "Index the required key (x[k]) so a missing key raises, or check for it "
        "and handle the absence explicitly. Keep .get() only for keys that are "
        "genuinely optional, and give it a default the caller can tell apart."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None or is_test_path(fi.relative_path):
                continue
            findings.extend(self._check_tree(fi.relative_path, tree))
        return findings

    def _check_tree(self, path: str, tree: ast.Module) -> list[Finding]:
        chained: dict[int, ast.Call] = {}
        inner: set[int] = set()
        for node in ast.walk(tree):
            if not _is_get_call(node):
                continue
            receiver = node.func.value  # type: ignore[attr-defined]
            defaulted = _empty_default_key(receiver)
            if defaulted is None or _has_visible_default(node):  # type: ignore[arg-type]
                continue
            chained[id(node)] = node  # type: ignore[assignment]
            inner.add(id(defaulted))
        findings: list[Finding] = []
        for node_id, node in chained.items():
            if node_id in inner:
                continue
            findings.append(
                self.finding(
                    file=path,
                    line=node.lineno,
                    key=_describe_key(self._first_defaulted(node)),
                )
            )
        return findings

    @staticmethod
    def _first_defaulted(outer: ast.Call) -> ast.Call:
        """Walk down the chain to the innermost ``.get`` that was given ``{}``."""
        first = outer
        current = _empty_default_key(outer.func.value)  # type: ignore[attr-defined]
        while current is not None:
            first = current
            current = _empty_default_key(current.func.value)  # type: ignore[attr-defined]
        return first


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

ERRORS_RULES = (
    BareExcept(),
    BroadTryBlock(),
    ErrorSwallowing(),
    ExceptPass(),
    InconsistentExceptions(),
    ExceptionInInit(),
    ChainedEmptyDefaultGet(),
)
