# ABOUTME: Service boundary rules mined from Newman Building Microservices (2nd ed.).
# ABOUTME: Detects coupling anti-patterns: hardcoded URLs, chatty integration, unversioned APIs.
from __future__ import annotations

import ast
import re

from gaudi.core import Category, Finding, Rule, Severity
from gaudi.packs.python.context import PythonContext


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
# Exported rule list
# ---------------------------------------------------------------

SERVICE_RULES = (
    HardcodedServiceURL(),
    ChattyIntegration(),
    NoAPIVersioning(),
)
