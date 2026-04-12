# ABOUTME: Stability rules mined from Nygard Release It! (2nd ed.).
# ABOUTME: Detects anti-patterns that cause production failures: unbounded resources, missing resilience.
from __future__ import annotations

import ast

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import PythonContext


def _parse_safe(source: str) -> ast.Module | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ---------------------------------------------------------------
# STAB-001  UnboundedResultSet
# Nygard Ch. 4: "Unbounded Result Sets" anti-pattern
# ---------------------------------------------------------------

_ORM_ALL_ATTRS = frozenset({"all", "filter", "exclude", "select_related", "prefetch_related"})
_BOUNDING_TERMINALS = frozenset({"first", "last", "get", "count", "exists", "aggregate"})


class UnboundedResultSet(Rule):
    """Detect ORM queries returning unbounded result sets.

    Principles: #4 (Failure must be named).
    Source: NYGARD Ch. 4 — Unbounded Result Sets anti-pattern.
    """

    code = "STAB-001"
    severity = Severity.WARN
    category = Category.STABILITY
    message_template = "Unbounded ORM query '.{method}()' at line {line}"
    recommendation_template = (
        "Add .limit(), slicing [:n], or pagination to ORM queries."
        " Unbounded result sets grow with data and eventually exhaust memory."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            bounded = self._collect_bounded_call_ids(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if id(node) in bounded:
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr not in _ORM_ALL_ATTRS:
                    continue
                if self._is_orm_chain(func):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                            method=func.attr,
                        )
                    )
        return findings

    @staticmethod
    def _collect_bounded_call_ids(tree: ast.Module) -> set[int]:
        """Find ORM Call nodes consumed by a bounding terminal like .first()."""
        bounded: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in _BOUNDING_TERMINALS:
                continue
            UnboundedResultSet._mark_chain_bounded(func.value, bounded)
        return bounded

    @staticmethod
    def _mark_chain_bounded(node: ast.expr, bounded: set[int]) -> None:
        """Walk down a method chain, marking every Call node as bounded."""
        if isinstance(node, ast.Call):
            bounded.add(id(node))
            if isinstance(node.func, ast.Attribute):
                UnboundedResultSet._mark_chain_bounded(node.func.value, bounded)

    @staticmethod
    def _is_orm_chain(func: ast.Attribute) -> bool:
        val = func.value
        if isinstance(val, ast.Attribute) and val.attr == "objects":
            return True
        if isinstance(val, ast.Call):
            if isinstance(val.func, ast.Attribute) and val.func.attr == "query":
                return True
        if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute):
            return UnboundedResultSet._is_orm_chain(val.func)
        return False


# ---------------------------------------------------------------
# STAB-003  RetryWithoutBackoff
# Nygard Ch. 5: Retry must include backoff to avoid thundering herd
# ---------------------------------------------------------------


class RetryWithoutBackoff(Rule):
    """Detect retry logic without exponential backoff.

    Principles: #4 (Failure must be named).
    Source: NYGARD Ch. 5 — Retry must include backoff to avoid thundering herds.
    """

    code = "STAB-003"
    severity = Severity.WARN
    category = Category.STABILITY
    message_template = "Retry without backoff at line {line}"
    recommendation_template = (
        "Add exponential backoff to retry logic."
        " Retries without backoff create thundering herds that amplify failures."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if self._is_tenacity_retry_without_backoff(node):
                    findings.append(self.finding(file=fi.relative_path, line=node.lineno))
                if self._is_urllib3_retry_without_backoff(node):
                    findings.append(self.finding(file=fi.relative_path, line=node.lineno))
        return findings

    @staticmethod
    def _is_tenacity_retry_without_backoff(node: ast.Call) -> bool:
        func = node.func
        name = ""
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "retry":
            return False
        kw_names = {kw.arg for kw in node.keywords}
        if "wait" in kw_names:
            return False
        if kw_names & {"stop", "retry", "reraise", "before", "after"}:
            return True
        return False

    @staticmethod
    def _is_urllib3_retry_without_backoff(node: ast.Call) -> bool:
        func = node.func
        name = ""
        if isinstance(func, ast.Name):
            name = func.id
        elif isinstance(func, ast.Attribute):
            name = func.attr
        if name != "Retry":
            return False
        kw_names = {kw.arg for kw in node.keywords}
        if "backoff_factor" in kw_names:
            return False
        if kw_names & {"total", "status_forcelist", "allowed_methods"}:
            return True
        return False


# ---------------------------------------------------------------
# STAB-004  UnboundedCache
# Nygard Ch. 5: "Steady State" -- resources must not grow without bound
# ---------------------------------------------------------------


class UnboundedCache(Rule):
    """Detect unbounded caches (lru_cache without maxsize, or @cache).

    Principles: #4 (Failure must be named).
    Source: NYGARD Ch. 5 — Steady State: unbounded resource growth.
    """

    code = "STAB-004"
    severity = Severity.WARN
    category = Category.STABILITY
    message_template = "Unbounded cache at line {line}"
    recommendation_template = (
        "Set a maxsize on @lru_cache or replace @cache with @lru_cache(maxsize=N)."
        " Unbounded caches grow until they exhaust memory."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for dec in node.decorator_list:
                    if self._is_unbounded_cache(dec):
                        findings.append(self.finding(file=fi.relative_path, line=dec.lineno))
        return findings

    @staticmethod
    def _is_unbounded_cache(dec: ast.expr) -> bool:
        if isinstance(dec, ast.Name) and dec.id == "cache":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "cache":
            return True
        if isinstance(dec, ast.Call):
            func = dec.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == "lru_cache":
                for kw in dec.keywords:
                    if kw.arg == "maxsize":
                        if isinstance(kw.value, ast.Constant) and kw.value.value is None:
                            return True
                return False
        return False


# ---------------------------------------------------------------
# STAB-005  BlockingInAsync
# Nygard Ch. 4: "Blocked Threads" anti-pattern
# ---------------------------------------------------------------

_BLOCKING_CALLS = frozenset(
    {
        "sleep",
        "get",
        "post",
        "put",
        "patch",
        "delete",
    }
)

_BLOCKING_MODULES = frozenset({"time", "requests"})


class BlockingInAsync(Rule):
    """Detect blocking calls inside async functions.

    Principles: #5 (State must be visible), #4 (Failure must be named).
    Source: NYGARD Ch. 4 — Blocked Threads anti-pattern.
    """

    code = "STAB-005"
    severity = Severity.ERROR
    category = Category.STABILITY
    message_template = "Blocking call '{call}' inside async function '{function}' at line {line}"
    recommendation_template = (
        "Use async equivalents (asyncio.sleep, httpx.AsyncClient) in async functions."
        " Blocking calls freeze the event loop and starve all concurrent tasks."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.AsyncFunctionDef):
                    continue
                for child in ast.walk(node):
                    if not isinstance(child, ast.Call):
                        continue
                    call_name = self._get_blocking_call(child)
                    if call_name:
                        findings.append(
                            self.finding(
                                file=fi.relative_path,
                                line=child.lineno,
                                call=call_name,
                                function=node.name,
                            )
                        )
        return findings

    @staticmethod
    def _get_blocking_call(node: ast.Call) -> str | None:
        func = node.func
        if not isinstance(func, ast.Attribute):
            return None
        if func.attr not in _BLOCKING_CALLS:
            return None
        val = func.value
        if isinstance(val, ast.Name) and val.id in _BLOCKING_MODULES:
            return f"{val.id}.{func.attr}"
        return None


# ---------------------------------------------------------------
# STAB-006  UnmanagedResource
# Nygard Ch. 5: "Steady State" -- close what you open
# Consolidates former SA-ARCH-001 (SQLAlchemy session leak)
# ---------------------------------------------------------------

_RESOURCE_CALLS = frozenset({"open", "Session", "connect", "Connection"})


class UnmanagedResource(Rule):
    """Detect resources opened without context-manager management.

    Principles: #4 (Failure must be named).
    Source: NYGARD Ch. 5 — Steady State: every resource has an owner.
    """

    code = "STAB-006"
    severity = Severity.WARN
    category = Category.STABILITY
    message_template = "Resource '{resource}' opened without context manager at line {line}"
    recommendation_template = (
        "Use a 'with' statement for resources that need cleanup."
        " Unmanaged resources leak file handles, connections, or sessions on exceptions."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            with_lines = self._collect_with_resource_lines(tree)

            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                resource_name = self._get_resource_name(node)
                if resource_name is None:
                    continue
                if node.lineno in with_lines:
                    continue
                if resource_name == "Session" and self._has_yield_nearby(node, fi.source):
                    continue
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=node.lineno,
                        resource=resource_name,
                    )
                )
        return findings

    @staticmethod
    def _get_resource_name(node: ast.Call) -> str | None:
        func = node.func
        if isinstance(func, ast.Name) and func.id in _RESOURCE_CALLS:
            return func.id
        if isinstance(func, ast.Attribute) and func.attr in _RESOURCE_CALLS:
            return func.attr
        return None

    @staticmethod
    def _has_yield_nearby(node: ast.Call, source: str) -> bool:
        lines = source.splitlines()
        start = max(0, node.lineno - 3)
        end = min(len(lines), node.lineno + 5)
        block = "\n".join(lines[start:end])
        return "yield" in block

    @staticmethod
    def _collect_with_resource_lines(tree: ast.Module) -> set[int]:
        lines: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.With, ast.AsyncWith)):
                continue
            for item in node.items:
                call = item.context_expr
                if isinstance(call, ast.Call):
                    func = call.func
                    if isinstance(func, ast.Name) and func.id in _RESOURCE_CALLS:
                        lines.add(call.lineno)
                    elif isinstance(func, ast.Attribute) and func.attr in _RESOURCE_CALLS:
                        lines.add(call.lineno)
        return lines


# ---------------------------------------------------------------
# STAB-007  UnboundedThreadPool
# Nygard Ch. 4: "Unbalanced Capacities" anti-pattern
# ---------------------------------------------------------------


class UnboundedThreadPool(Rule):
    """Detect ThreadPoolExecutor instantiated without max_workers.

    Principles: #4 (Failure must be named).
    Source: NYGARD Ch. 4 — Unbalanced Capacities anti-pattern.
    """

    code = "STAB-007"
    severity = Severity.WARN
    category = Category.STABILITY
    message_template = "ThreadPoolExecutor without max_workers at line {line}"
    recommendation_template = (
        "Set max_workers on ThreadPoolExecutor."
        " Without a bound, thread creation scales with demand"
        " and can exhaust system resources under load."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = ""
                if isinstance(func, ast.Name):
                    name = func.id
                elif isinstance(func, ast.Attribute):
                    name = func.attr
                if name != "ThreadPoolExecutor":
                    continue
                kw_names = {kw.arg for kw in node.keywords}
                has_positional_max = len(node.args) >= 1
                if "max_workers" not in kw_names and not has_positional_max:
                    findings.append(self.finding(file=fi.relative_path, line=node.lineno))
        return findings


# ---------------------------------------------------------------
# STAB-008  IntegrationPointNoFallback
# Nygard Ch. 4: "Integration Points" -- every integration must degrade
# ---------------------------------------------------------------

_HTTP_MODULES = frozenset({"requests", "httpx"})
_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "request", "head", "options"})


class IntegrationPointNoFallback(Rule):
    """Detect external HTTP calls that have no try/except fallback path.

    Principles: #4 (Failure must be named).
    Source: NYGARD Ch. 4 -- Integration Points are the leading source of cracks.
    """

    code = "STAB-008"
    severity = Severity.WARN
    category = Category.STABILITY
    # Fallbacks are Resilient catechism #5. Pragmatic adds them when
    # abuse materializes; Unix "worse is better" tolerates partial
    # failure; Functional/Data-Oriented treat this as out of scope.
    philosophy_scope = frozenset({"classical", "resilient", "convention", "event-sourced"})
    message_template = "External call '{call}' without fallback at line {line}"
    recommendation_template = (
        "Wrap external HTTP calls in try/except so the caller can degrade."
        " An integration point with no fallback propagates every upstream failure."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            try_lines = self._collect_try_body_lines(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                call_name = self._get_http_call(node)
                if call_name is None:
                    continue
                if node.lineno in try_lines:
                    continue
                findings.append(
                    self.finding(file=fi.relative_path, line=node.lineno, call=call_name)
                )
        return findings

    @staticmethod
    def _get_http_call(node: ast.Call) -> str | None:
        func = node.func
        if not isinstance(func, ast.Attribute):
            return None
        if func.attr not in _HTTP_METHODS:
            return None
        val = func.value
        if isinstance(val, ast.Name) and val.id in _HTTP_MODULES:
            return f"{val.id}.{func.attr}"
        return None

    @staticmethod
    def _collect_try_body_lines(tree: ast.Module) -> set[int]:
        lines: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            if not node.handlers:
                continue
            for stmt in node.body:
                for child in ast.walk(stmt):
                    if hasattr(child, "lineno"):
                        lines.add(child.lineno)
        return lines


# ---------------------------------------------------------------
# STAB-009  FailFastLateValidation
# Nygard Ch. 5: "Fail Fast" -- validate at entry, not deep in helpers
# ---------------------------------------------------------------

_VALIDATION_EXCEPTIONS = frozenset({"TypeError", "ValueError"})


class FailFastLateValidation(Rule):
    """Detect argument validation hidden inside private helper functions.

    Principles: #4 (Failure must be named).
    Source: NYGARD Ch. 5 -- Fail Fast: validate at the boundary, not down the stack.
    """

    code = "STAB-009"
    severity = Severity.WARN
    category = Category.STABILITY
    message_template = "Late argument validation inside private helper '{function}' at line {line}"
    recommendation_template = (
        "Move isinstance/value-range checks to the public entry point."
        " Validation in private helpers means callers fail deep in the stack instead of at the boundary."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not self._is_private_helper(node.name):
                    continue
                hit = self._find_validation(node)
                if hit is not None:
                    findings.append(
                        self.finding(file=fi.relative_path, line=hit, function=node.name)
                    )
        return findings

    @staticmethod
    def _is_private_helper(name: str) -> bool:
        return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))

    @staticmethod
    def _find_validation(func: ast.FunctionDef | ast.AsyncFunctionDef) -> int | None:
        for node in ast.walk(func):
            if not isinstance(node, ast.If):
                continue
            if not FailFastLateValidation._test_uses_isinstance(node.test):
                continue
            for stmt in node.body:
                if isinstance(stmt, ast.Raise) and FailFastLateValidation._raises_validation(stmt):
                    return node.lineno
        return None

    @staticmethod
    def _test_uses_isinstance(test: ast.expr) -> bool:
        for child in ast.walk(test):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Name) and func.id == "isinstance":
                    return True
        return False

    @staticmethod
    def _raises_validation(stmt: ast.Raise) -> bool:
        exc = stmt.exc
        if exc is None:
            return False
        if isinstance(exc, ast.Call):
            exc = exc.func
        if isinstance(exc, ast.Name) and exc.id in _VALIDATION_EXCEPTIONS:
            return True
        if isinstance(exc, ast.Attribute) and exc.attr in _VALIDATION_EXCEPTIONS:
            return True
        return False


# ---------------------------------------------------------------
# STAB-010  SharedResourcePool
# Nygard Ch. 5: "Bulkheads" -- partition resource pools by concern
# ---------------------------------------------------------------


class SharedResourcePool(Rule):
    """Detect module-level ThreadPoolExecutor instances (no bulkhead).

    Principles: #4 (Failure must be named).
    Source: NYGARD Ch. 5 -- Bulkheads: partition pools so one failure can't sink the ship.
    """

    code = "STAB-010"
    severity = Severity.INFO
    category = Category.STABILITY
    # Bulkheads (Nygard Ch. 5) are Resilient catechism #4. Schools
    # that do not operate at the scale where bulkheads matter, or
    # that consider the pattern premature, are excluded.
    philosophy_scope = frozenset({"classical", "resilient", "event-sourced"})
    message_template = "Module-level ThreadPoolExecutor at line {line} -- shared by all callers"
    recommendation_template = (
        "Scope ThreadPoolExecutors to a single concern, or partition by workload."
        " A single shared pool means a slow consumer can starve every other caller."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            for node in tree.body:
                target = self._extract_assigned_call(node)
                if target is None:
                    continue
                if self._is_thread_pool_call(target):
                    findings.append(self.finding(file=fi.relative_path, line=target.lineno))
        return findings

    @staticmethod
    def _extract_assigned_call(node: ast.stmt) -> ast.Call | None:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.value, ast.Call):
            return node.value
        return None

    @staticmethod
    def _is_thread_pool_call(call: ast.Call) -> bool:
        func = call.func
        if isinstance(func, ast.Name) and func.id == "ThreadPoolExecutor":
            return True
        if isinstance(func, ast.Attribute) and func.attr == "ThreadPoolExecutor":
            return True
        return False


# ---------------------------------------------------------------
# STAB-011  MissingHealthEndpoint
# Nygard Ch. 5: "Handshaking" -- services must advertise health
# ---------------------------------------------------------------

_WEB_LIBRARIES = frozenset({"fastapi", "flask", "django"})
_ROUTE_DECORATOR_ATTRS = frozenset({"get", "post", "put", "patch", "delete", "route"})
_HEALTH_TOKENS = ("health", "ready", "live", "ping")


class MissingHealthEndpoint(Rule):
    """Detect web services with routes but no /health or /ready endpoint.

    Principles: #4 (Failure must be named), #5 (State must be visible).
    Source: NYGARD Ch. 5 -- Handshaking: services must advertise their state.
    """

    code = "STAB-011"
    severity = Severity.INFO
    category = Category.STABILITY
    # Health checks are a long-lived-service concept. One-shot Unix
    # scripts and Data-Oriented batch jobs have no meaningful health.
    philosophy_scope = frozenset(
        {
            "classical",
            "pragmatic",
            "functional",
            "resilient",
            "convention",
            "event-sourced",
        }
    )
    message_template = "Web service has no health or ready endpoint"
    recommendation_template = (
        "Add a /health or /ready route so orchestrators and load balancers"
        " can detect failure. A service with no health endpoint is invisible to its operators."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        if not (context.detected_libraries & _WEB_LIBRARIES):
            return []
        any_route = False
        has_health = False
        first_route_file: str | None = None
        for fi in context.files:
            tree = _parse_safe(fi.source)
            if tree is None:
                continue
            for path in self._iter_route_paths(tree):
                any_route = True
                if first_route_file is None:
                    first_route_file = fi.relative_path
                if any(token in path.lower() for token in _HEALTH_TOKENS):
                    has_health = True
        if not any_route or has_health:
            return []
        return [self.finding(file=first_route_file, line=1)]

    @staticmethod
    def _iter_route_paths(tree: ast.Module) -> list[str]:
        paths: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if MissingHealthEndpoint._is_route_call(node):
                    literal = MissingHealthEndpoint._first_string_arg(node)
                    if literal is not None:
                        paths.append(literal)
        return paths

    @staticmethod
    def _is_route_call(call: ast.Call) -> bool:
        func = call.func
        if isinstance(func, ast.Attribute) and func.attr in _ROUTE_DECORATOR_ATTRS:
            return True
        if isinstance(func, ast.Name) and func.id in {"path", "re_path", "url"}:
            return True
        return False

    @staticmethod
    def _first_string_arg(call: ast.Call) -> str | None:
        if not call.args:
            return None
        first = call.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
        return None


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

STABILITY_RULES = (
    UnboundedResultSet(),
    RetryWithoutBackoff(),
    UnboundedCache(),
    BlockingInAsync(),
    UnmanagedResource(),
    UnboundedThreadPool(),
    IntegrationPointNoFallback(),
    FailFastLateValidation(),
    SharedResourcePool(),
    MissingHealthEndpoint(),
)
