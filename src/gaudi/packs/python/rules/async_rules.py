# ABOUTME: Concurrency / async rules covering shared mutable state, missing async
# ABOUTME: context managers, mixed sync/async modules, and missing graceful shutdown.
from __future__ import annotations

import ast

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# ASYNC-001  SharedMutableStateAcrossThreads
# Nygard Ch. 4: shared mutable state across threads is a race waiting to happen.
# ---------------------------------------------------------------

_THREAD_SUBMIT_NAMES = frozenset({"ThreadPoolExecutor", "Thread"})


def _functions_using_thread_pool(tree: ast.Module) -> set[str]:
    """Return the names of functions referenced as workers for threads/pools.

    Looks for ThreadPoolExecutor().submit(worker, ...), pool.map(worker, ...),
    and threading.Thread(target=worker).
    """
    workers: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # pool.submit(fn, ...) / pool.map(fn, ...)
        if isinstance(func, ast.Attribute) and func.attr in {"submit", "map"}:
            if node.args and isinstance(node.args[0], ast.Name):
                workers.add(node.args[0].id)
        # threading.Thread(target=fn)
        if isinstance(func, ast.Attribute) and func.attr == "Thread":
            for kw in node.keywords:
                if kw.arg == "target" and isinstance(kw.value, ast.Name):
                    workers.add(kw.value.id)
        if isinstance(func, ast.Name) and func.id == "Thread":
            for kw in node.keywords:
                if kw.arg == "target" and isinstance(kw.value, ast.Name):
                    workers.add(kw.value.id)
    return workers


def _function_mutates(func: ast.FunctionDef | ast.AsyncFunctionDef, names: set[str]) -> str | None:
    """Return the first module-level name mutated inside this function, if any."""
    for child in ast.walk(func):
        # name[k] = v
        if isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name):
                    if target.value.id in names:
                        return target.value.id
        # name.append(...), name.update(...), name.add(...), name.pop(...)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            if child.func.attr in {
                "append",
                "extend",
                "update",
                "add",
                "pop",
                "setdefault",
                "clear",
            }:
                if isinstance(child.func.value, ast.Name) and child.func.value.id in names:
                    return child.func.value.id
    return None


class SharedMutableStateAcrossThreads(Rule):
    """Detect module-level mutables mutated inside functions run on a thread pool.

    Principles: #4 (Failure must be named), #5 (State must be visible).
    Source: NYGARD Ch. 4 — concurrent mutation of shared state.
    """

    code = "ASYNC-001"
    severity = Severity.ERROR
    category = Category.CONCURRENCY
    message_template = (
        "Shared module-level mutable '{name}' mutated inside thread pool worker"
        " '{function}' at line {line}"
    )
    recommendation_template = (
        "Move shared state into a thread-safe container (queue.Queue, threading.Lock-guarded"
        " dict) or return values from the worker and merge on the main thread."
        " Concurrent mutation of plain dict/list/set is a race condition."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            mutables = _collect_module_mutables(tree)
            if not mutables:
                continue
            workers = _functions_using_thread_pool(tree)
            if not workers:
                continue
            mutable_names = set(mutables)
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if node.name not in workers:
                    continue
                hit = _function_mutates(node, mutable_names)
                if hit is not None:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                            name=hit,
                            function=node.name,
                        )
                    )
        return findings


def _collect_module_mutables(tree: ast.Module) -> dict[str, int]:
    mutables: dict[str, int] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, (ast.Dict, ast.List, ast.Set)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                mutables[target.id] = node.lineno
    return mutables


# ---------------------------------------------------------------
# ASYNC-002  MissingAsyncContextManager
# aiohttp/httpx async clients leak connections without async with.
# ---------------------------------------------------------------

_ASYNC_CLIENT_NAMES = frozenset({"ClientSession", "AsyncClient"})


class MissingAsyncContextManager(Rule):
    """Detect aiohttp.ClientSession() / httpx.AsyncClient() not inside async with.

    Principles: #4 (Failure must be named).
    Source: aiohttp + httpx documentation -- session lifetime must be scoped.
    """

    code = "ASYNC-002"
    severity = Severity.WARN
    category = Category.CONCURRENCY
    message_template = "{client} created without async with at line {line}"
    recommendation_template = (
        "Wrap async HTTP clients in 'async with': they hold a connection pool"
        " that leaks unless the session is explicitly closed."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            managed_lines = _collect_async_with_call_lines(tree)
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                client = _async_client_name(node.func)
                if client is None:
                    continue
                if node.lineno in managed_lines:
                    continue
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=node.lineno,
                        client=client,
                    )
                )
        return findings


def _async_client_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name) and func.id in _ASYNC_CLIENT_NAMES:
        return func.id
    if isinstance(func, ast.Attribute) and func.attr in _ASYNC_CLIENT_NAMES:
        return func.attr
    return None


def _collect_async_with_call_lines(tree: ast.Module) -> set[int]:
    lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.With, ast.AsyncWith)):
            continue
        for item in node.items:
            expr = item.context_expr
            if isinstance(expr, ast.Call) and _async_client_name(expr.func) is not None:
                lines.add(expr.lineno)
    return lines


# ---------------------------------------------------------------
# ASYNC-003  MixedSyncAsyncModule
# A module that mixes async def with sync requests.* calls is architecturally
# confused -- one of the two will block the other.
# ---------------------------------------------------------------

_REQUESTS_METHODS = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "request"}
)


class MixedSyncAsyncModule(Rule):
    """Detect modules that mix async def with sync requests.* calls.

    Principles: #2 (One concept, one home), #5 (State must be visible).
    Source: FastAPI/aiohttp documentation -- never mix sync HTTP with async code.
    """

    code = "ASYNC-003"
    severity = Severity.WARN
    category = Category.CONCURRENCY
    message_template = "Module mixes async def with sync requests.{method}() at line {line}"
    recommendation_template = (
        "Pick one: use httpx.AsyncClient/aiohttp throughout the module, or remove the"
        " async def. Sync HTTP inside an async module blocks the event loop."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            if _looks_like_test_file(fi.relative_path):
                continue
            tree = fi.ast_tree
            if tree is None:
                continue
            if not _has_async_function(tree):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                method = _requests_method_name(node.func)
                if method is None:
                    continue
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=node.lineno,
                        method=method,
                    )
                )
        return findings


def _has_async_function(tree: ast.Module) -> bool:
    return any(isinstance(n, ast.AsyncFunctionDef) for n in ast.walk(tree))


def _requests_method_name(func: ast.expr) -> str | None:
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr not in _REQUESTS_METHODS:
        return None
    val = func.value
    if isinstance(val, ast.Name) and val.id == "requests":
        return func.attr
    return None


def _looks_like_test_file(relative_path: str) -> bool:
    norm = relative_path.replace("\\", "/").lower()
    if "/tests/" in norm or norm.startswith("tests/"):
        return True
    name = norm.rsplit("/", 1)[-1]
    return name.startswith("test_") or name.endswith("_test.py")


# ---------------------------------------------------------------
# ASYNC-004  NoGracefulShutdown
# asyncio.run() without signal handler registration -- the service has no way
# to drain in-flight work on SIGTERM.
# ---------------------------------------------------------------


class NoGracefulShutdown(Rule):
    """Detect asyncio.run() in modules with no signal.signal() registration.

    Principles: #4 (Failure must be named), #14 (Reversibility is a design property).
    Source: Python asyncio best practices -- long-running services need shutdown hooks.
    """

    code = "ASYNC-004"
    severity = Severity.INFO
    category = Category.CONCURRENCY
    message_template = "asyncio.run() at line {line} without signal handler registration"
    recommendation_template = (
        "Register a signal.signal(SIGTERM, ...) handler before asyncio.run() so the"
        " service can drain in-flight work on shutdown."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            if _looks_like_test_file(fi.relative_path):
                continue
            tree = fi.ast_tree
            if tree is None:
                continue
            run_calls: list[ast.Call] = []
            has_signal_register = False
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if _is_asyncio_run(node.func):
                    run_calls.append(node)
                if _is_signal_register(node.func):
                    has_signal_register = True
            if has_signal_register or not run_calls:
                continue
            for call in run_calls:
                findings.append(self.finding(file=fi.relative_path, line=call.lineno))
        return findings


def _is_asyncio_run(func: ast.expr) -> bool:
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr != "run":
        return False
    return isinstance(func.value, ast.Name) and func.value.id == "asyncio"


def _is_signal_register(func: ast.expr) -> bool:
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr not in {"signal", "add_signal_handler"}:
        return False
    if isinstance(func.value, ast.Name) and func.value.id == "signal":
        return True
    # loop.add_signal_handler(...)
    if func.attr == "add_signal_handler":
        return True
    return False


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

ASYNC_RULES = (
    SharedMutableStateAcrossThreads(),
    MissingAsyncContextManager(),
    MixedSyncAsyncModule(),
    NoGracefulShutdown(),
)
