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


class UnboundedResultSet(Rule):
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
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
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
                    findings.append(
                        self.finding(file=fi.relative_path, line=node.lineno)
                    )
                if self._is_urllib3_retry_without_backoff(node):
                    findings.append(
                        self.finding(file=fi.relative_path, line=node.lineno)
                    )
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
                        findings.append(
                            self.finding(file=fi.relative_path, line=dec.lineno)
                        )
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

_BLOCKING_CALLS = frozenset({
    "sleep",
    "get",
    "post",
    "put",
    "patch",
    "delete",
})

_BLOCKING_MODULES = frozenset({"time", "requests"})


class BlockingInAsync(Rule):
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
                    findings.append(
                        self.finding(file=fi.relative_path, line=node.lineno)
                    )
        return findings


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
)
