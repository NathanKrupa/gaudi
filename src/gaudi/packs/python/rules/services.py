# ABOUTME: Service boundary rules mined from Newman Building Microservices (2nd ed.).
# ABOUTME: Detects coupling anti-patterns: hardcoded URLs, chatty integration, unversioned APIs.
from __future__ import annotations

import ast
import re
from urllib.parse import urlparse

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import FileInfo, PythonContext


def _parse_safe(source: str) -> ast.Module | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


# ---------------------------------------------------------------
# SVC-001  HardcodedServiceURL
# Newman Ch. 5: Service endpoints should be config-injected,
# not baked into source code.
# ---------------------------------------------------------------

_HARDCODED_URL_RE = re.compile(
    r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?",
)


class HardcodedServiceURL(Rule):
    """Detect hardcoded service URLs (localhost, 127.0.0.1, etc.).

    Principles: #5 (State must be visible).
    Source: NEWMAN Ch. 5 — service discovery: endpoints are configuration.
    """

    code = "SVC-001"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Hardcoded service URL '{url}' at line {line}"
    recommendation_template = (
        "Inject service URLs via configuration (environment variables or config files)."
        " Hardcoded URLs break when services move, scale, or deploy to new environments."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            # Skip test files
            if "test" in fi.relative_path.lower():
                continue
            for i, line in enumerate(fi.source.splitlines(), 1):
                # Skip comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                match = _HARDCODED_URL_RE.search(line)
                if match:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=i,
                            url=match.group(1),
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SVC-002  ChattyIntegration
# Newman Ch. 4: Chatty service calls indicate a missing
# batch or aggregate endpoint.
# ---------------------------------------------------------------

_HTTP_CALL_ATTRS = frozenset({"get", "post", "put", "patch", "delete", "request", "fetch"})
_HTTP_MODULES = frozenset({"requests", "httpx", "aiohttp", "client", "session"})


class ChattyIntegration(Rule):
    """Detect functions making many HTTP calls (chatty integration).

    Principles: #10 (Boundaries are real or fictional).
    Source: NEWMAN Ch. 4 — chatty service boundary.
    """

    code = "SVC-002"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = "Function '{function}' makes {count} HTTP calls -- consider batching"
    recommendation_template = (
        "Multiple sequential HTTP calls to external services suggest a missing"
        " batch or aggregate endpoint. Consolidate into fewer, larger requests."
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
                count = self._count_http_calls(node)
                if count >= 3:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                            function=node.name,
                            count=count,
                        )
                    )
        return findings

    @staticmethod
    def _count_http_calls(func_node: ast.AST) -> int:
        count = 0
        for child in ast.walk(func_node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in _HTTP_CALL_ATTRS:
                continue
            val = func.value
            if isinstance(val, ast.Name) and val.id.lower() in _HTTP_MODULES:
                count += 1
            elif isinstance(val, ast.Attribute) and val.attr.lower() in _HTTP_MODULES:
                count += 1
            elif isinstance(val, ast.Name) and val.id == "self":
                # self.session.get() etc
                pass
        return count


# ---------------------------------------------------------------
# SVC-003  NoAPIVersioning
# Newman Ch. 7: API endpoints should include version prefix
# for safe evolution.
# ---------------------------------------------------------------

_VERSION_RE = re.compile(r"/v\d+")
_ROUTE_DECORATOR_RE = re.compile(r"@\w+\.(get|post|put|patch|delete|route|api_route)\s*\(")


class NoAPIVersioning(Rule):
    """Detect API endpoints without a version prefix.

    Principles: #14 (Reversibility is a design property).
    Source: NEWMAN Ch. 7 — API versioning enables safe evolution.
    """

    code = "SVC-003"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    message_template = "API endpoint without version prefix at line {line}"
    recommendation_template = (
        "Add a version prefix (e.g. '/v1/...') to API routes."
        " Versioned APIs allow safe evolution without breaking existing clients."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            has_api_framework = fi.has_import("fastapi") or fi.has_import("flask")
            if not has_api_framework:
                continue
            for i, line in enumerate(fi.source.splitlines(), 1):
                if not _ROUTE_DECORATOR_RE.search(line):
                    continue
                # Check decorator and next line for version pattern
                block = line
                source_lines = fi.source.splitlines()
                if i < len(source_lines):
                    block += source_lines[i]
                if _VERSION_RE.search(block):
                    continue
                # Skip health/ready endpoints
                if any(p in block for p in ["/health", "/ready", "/ping", "/docs", "/openapi"]):
                    continue
                findings.append(self.finding(file=fi.relative_path, line=i))
        return findings


# ---------------------------------------------------------------
# SVC-004  SharedDatabasePattern
# Newman Ch. 4: Two services reading the same table is a hidden
# coupling -- the schema becomes a public contract no one signed.
# ---------------------------------------------------------------


def _importer_app(relative_path: str) -> str | None:
    """Return the Django app name an importing file lives in.

    Recognises ``apps/<name>/...`` layouts and falls back to the first path
    segment for top-level app directories like ``users/views.py``.
    """
    parts = relative_path.replace("\\", "/").split("/")
    if len(parts) < 2:
        return None
    if parts[0] == "apps" and len(parts) >= 3:
        return parts[1]
    return parts[0]


def _model_module_owner(module: str) -> str | None:
    """Given an import module like ``apps.users.models``, return ``users``."""
    if not module:
        return None
    segments = module.split(".")
    if "models" not in segments:
        return None
    idx = segments.index("models")
    if idx == 0:
        return None
    return segments[idx - 1]


class SharedDatabasePattern(Rule):
    """Detect a model imported by 2+ external Django apps (shared database).

    Principles: #10 (Boundaries are real or fictional), #1 (The structure tells the story).
    Source: NEWMAN Ch. 4 -- shared database is the canonical hidden coupling.
    """

    code = "SVC-004"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    requires_library = "django"
    message_template = (
        "Model '{model}' from app '{owner}' is imported by {count} other apps"
        " ({importers}) -- shared database coupling"
    )
    recommendation_template = (
        "Two services reading the same table is a hidden contract no one signed."
        " Expose the data through the owning app's service layer (a function or"
        " API) so the schema can change without breaking unrelated apps."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        # (owner_app, model_name) -> list[(file, line, importer_app)]
        usages: dict[tuple[str, str], list[tuple[str, int, str]]] = {}
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            importer_app = _importer_app(fi.relative_path)
            if importer_app is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.module is None:
                    continue
                owner = _model_module_owner(node.module)
                if owner is None or owner == importer_app:
                    continue
                for alias in node.names:
                    key = (owner, alias.name)
                    usages.setdefault(key, []).append((fi.relative_path, node.lineno, importer_app))

        findings: list[Finding] = []
        for (owner, model), records in usages.items():
            distinct_apps = {app for _, _, app in records}
            if len(distinct_apps) < 2:
                continue
            importers_label = ", ".join(sorted(distinct_apps))
            for file, line, _ in records:
                findings.append(
                    self.finding(
                        file=file,
                        line=line,
                        model=model,
                        owner=owner,
                        count=len(distinct_apps),
                        importers=importers_label,
                    )
                )
        return findings


# ---------------------------------------------------------------
# SVC-005  SynchronousCouplingChain
# Newman Ch. 4: Sequential sync HTTP calls to multiple services
# tie the caller's latency and reliability to the slowest peer.
# ---------------------------------------------------------------

_HTTP_METHODS = frozenset({"get", "post", "put", "patch", "delete", "head", "options", "request"})
_HTTP_LIBS = frozenset({"requests", "httpx", "urllib3"})
_PARALLEL_NAMES = frozenset(
    {"gather", "wait", "as_completed", "ThreadPoolExecutor", "ProcessPoolExecutor"}
)


def _call_first_string(call: ast.Call) -> str | None:
    """Return the leading literal of the call's first positional argument, if any."""
    if not call.args:
        return None
    arg = call.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    if isinstance(arg, ast.JoinedStr):
        for piece in arg.values:
            if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                return piece.value
            return None
    return None


def _http_call_host(call: ast.Call) -> str | None:
    """If this call is a sync HTTP client call, return the host of its URL."""
    func = call.func
    if not isinstance(func, ast.Attribute) or func.attr not in _HTTP_METHODS:
        return None
    root = func.value
    if isinstance(root, ast.Name) and root.id.lower() in _HTTP_LIBS:
        pass
    elif isinstance(root, ast.Attribute) and root.attr.lower() in _HTTP_LIBS:
        pass
    else:
        return None
    url = _call_first_string(call)
    if not url:
        return None
    parsed = urlparse(url)
    return parsed.netloc or None


def _has_parallel_dispatch(func_node: ast.AST) -> bool:
    """Detect asyncio.gather / ThreadPoolExecutor / similar fan-out helpers."""
    for child in ast.walk(func_node):
        if isinstance(child, ast.Call):
            target = child.func
            name = None
            if isinstance(target, ast.Attribute):
                name = target.attr
            elif isinstance(target, ast.Name):
                name = target.id
            if name in _PARALLEL_NAMES:
                return True
    return False


class SynchronousCouplingChain(Rule):
    """Detect a sync function fanning out to 2+ distinct upstream services.

    Principles: #10 (Boundaries are real or fictional), #11 (Bounded resources).
    Source: NEWMAN Ch. 4 -- synchronous chains compound latency and failure.
    """

    code = "SVC-005"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = (
        "Function '{function}' makes sync calls to {count} services ({hosts})"
        " -- synchronous coupling chain"
    )
    recommendation_template = (
        "Sequential sync calls to multiple services tie the caller's latency and"
        " reliability to the slowest peer. Fan out in parallel (asyncio.gather,"
        " a thread pool) or pull the data through a single aggregating endpoint."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            if "test" in fi.relative_path.lower():
                continue
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                hosts: list[str] = []
                for child in ast.walk(node):
                    if not isinstance(child, ast.Call):
                        continue
                    host = _http_call_host(child)
                    if host:
                        hosts.append(host)
                distinct = sorted(set(hosts))
                if len(distinct) < 2:
                    continue
                if _has_parallel_dispatch(node):
                    continue
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=node.lineno,
                        function=node.name,
                        count=len(distinct),
                        hosts=", ".join(distinct),
                    )
                )
        return findings


# ---------------------------------------------------------------
# SVC-006  MissingContractTests
# Newman Ch. 7: A module that talks to an external service is a
# contract surface; it needs a paired test that pins the contract.
# ---------------------------------------------------------------


def _is_test_path(relative_path: str) -> bool:
    posix = relative_path.replace("\\", "/").lower()
    if posix.startswith("tests/") or "/tests/" in posix:
        return True
    name = posix.rsplit("/", 1)[-1]
    return name.startswith("test_") or name.endswith("_test.py")


def _has_outbound_http_call(fi: FileInfo) -> bool:
    tree = fi.ast_tree
    if tree is None:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _http_call_host(node) is not None:
            return True
        # Catch calls without literal URLs too -- requests.get(url_var)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in _HTTP_METHODS:
                root = func.value
                if isinstance(root, ast.Name) and root.id.lower() in _HTTP_LIBS:
                    return True
                if isinstance(root, ast.Attribute) and root.attr.lower() in _HTTP_LIBS:
                    return True
    return False


class MissingContractTests(Rule):
    """Detect HTTP client modules without a paired test file.

    Principles: #14 (Reversibility is a design property), #10 (Boundaries are real or fictional).
    Source: NEWMAN Ch. 7 -- consumer-driven contracts protect cross-service evolution.
    """

    code = "SVC-006"
    severity = Severity.INFO
    category = Category.ARCHITECTURE
    requires_library = "requests"
    message_template = (
        "Module '{module}' calls external services but has no paired test"
        " (expected test_{module}.py)"
    )
    recommendation_template = (
        "A module that talks to an external service is a contract surface."
        " Add a test that exercises the request shape -- even a mock-based one --"
        " so a remote API change cannot pass CI silently."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        test_stems: set[str] = set()
        for fi in context.files:
            name = fi.relative_path.replace("\\", "/").rsplit("/", 1)[-1]
            if name.startswith("test_") and name.endswith(".py"):
                test_stems.add(name[len("test_") : -len(".py")])
            elif name.endswith("_test.py"):
                test_stems.add(name[: -len("_test.py")])

        findings: list[Finding] = []
        for fi in context.files:
            if _is_test_path(fi.relative_path):
                continue
            name = fi.relative_path.replace("\\", "/").rsplit("/", 1)[-1]
            if name == "__init__.py" or not name.endswith(".py"):
                continue
            stem = name[: -len(".py")]
            if stem in test_stems:
                continue
            if not _has_outbound_http_call(fi):
                continue
            findings.append(
                self.finding(
                    file=fi.relative_path,
                    line=1,
                    module=stem,
                )
            )
        return findings


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

SERVICE_RULES = (
    HardcodedServiceURL(),
    ChattyIntegration(),
    NoAPIVersioning(),
    SharedDatabasePattern(),
    SynchronousCouplingChain(),
    MissingContractTests(),
)
