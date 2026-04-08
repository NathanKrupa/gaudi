# ABOUTME: Logging hygiene rules -- structured output, sensitive data, logger
# ABOUTME: naming, print misuse, and request correlation in endpoint handlers.
from __future__ import annotations

import ast
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import FileInfo, PythonContext


# ---------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------

_LOG_METHODS = frozenset(
    {
        "info",
        "warning",
        "debug",
        "error",
    }
)

# Broader set used by LOG-002 / LOG-005. LOG-001 keeps its narrower set so its
# behavior does not shift under us.
_LOG_METHODS_ALL = frozenset(
    {
        "info",
        "warning",
        "warn",
        "debug",
        "error",
        "critical",
        "exception",
        "log",
    }
)


def _is_logger_call(call: ast.Call) -> bool:
    func = call.func
    return isinstance(func, ast.Attribute) and func.attr in _LOG_METHODS_ALL


# ---------------------------------------------------------------
# LOG-001  UnstructuredLogging
# ---------------------------------------------------------------


class UnstructuredLogging(Rule):
    """Detect f-strings in logger calls (use lazy %-formatting).

    Principles: #13 (The system must explain itself).
    Source: ARCH90 Day 5 -- structured logging is how the system explains itself.
    """

    code = "LOG-001"
    severity = Severity.INFO
    category = Category.LOGGING
    message_template = "f-string in logger call at line {line} -- use %-formatting"
    recommendation_template = (
        "Use logger.info('message %s', var) instead of"
        " logger.info(f'message {{var}}'). Lazy formatting"
        " avoids string construction when log level"
        " is disabled."
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
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr not in _LOG_METHODS:
                    continue
                if not node.args:
                    continue
                if isinstance(node.args[0], ast.JoinedStr):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# LOG-002  SensitiveDataInLog
# ---------------------------------------------------------------

_SENSITIVE_NAME_PATTERNS: tuple[str, ...] = (
    "password",
    "passwd",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "private_key",
    "credit_card",
    "creditcard",
    "credential",
    "ssn",
)
# "token" and "pwd" handled separately as standalone-or-suffix matches to keep
# false positives down (avoid matching "tokenizer", "spwd").
_SENSITIVE_EXACT: frozenset[str] = frozenset({"token", "pwd"})


def _is_sensitive_name(name: str) -> bool:
    lower = name.lower()
    if lower in _SENSITIVE_EXACT:
        return True
    if any(part in _SENSITIVE_EXACT for part in lower.split("_")):
        return True
    return any(pat in lower for pat in _SENSITIVE_NAME_PATTERNS)


def _references_sensitive(node: ast.AST) -> bool:
    """Return True if any Name, Attribute, or string Dict-key under node is sensitive."""
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and _is_sensitive_name(child.id):
            return True
        if isinstance(child, ast.Attribute) and _is_sensitive_name(child.attr):
            return True
        if isinstance(child, ast.Dict):
            for key in child.keys:
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and _is_sensitive_name(key.value)
                ):
                    return True
    return False


class SensitiveDataInLog(Rule):
    """Detect logger calls whose arguments reference sensitive variable names.

    Principles: #2 (Surface area reflects power), #13 (The system must explain itself).
    Source: OWASP Logging Cheat Sheet -- never log credentials, tokens, or PII.
    """

    code = "LOG-002"
    severity = Severity.WARN
    category = Category.LOGGING
    message_template = (
        "Logger call at line {line} references a sensitive name (password / token / api_key / ...)"
    )
    recommendation_template = (
        "Logs leak. Never include passwords, tokens, API keys, SSNs, or other"
        " credentials in log records -- not as positional args, not in f-strings,"
        " and not as `extra=` fields. Log an opaque user id or hashed handle instead."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not _is_logger_call(node):
                    continue
                if self._call_is_sensitive(node):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings

    def _call_is_sensitive(self, call: ast.Call) -> bool:
        for arg in call.args:
            if _references_sensitive(arg):
                return True
        for kw in call.keywords:
            if kw.value is not None and _references_sensitive(kw.value):
                return True
        return False


# ---------------------------------------------------------------
# LOG-003  InconsistentLoggerName
# ---------------------------------------------------------------


def _is_get_logger_call(call: ast.Call) -> bool:
    func = call.func
    if isinstance(func, ast.Attribute) and func.attr == "getLogger":
        return True
    if isinstance(func, ast.Name) and func.id == "getLogger":
        return True
    return False


class InconsistentLoggerName(Rule):
    """Detect getLogger called with a hardcoded string instead of __name__.

    Principles: #13 (The system must explain itself).
    Source: Python logging docs -- using __name__ propagates the module hierarchy
    so log filters and handlers compose predictably.
    """

    code = "LOG-003"
    severity = Severity.INFO
    category = Category.LOGGING
    message_template = "getLogger called with hardcoded string at line {line} -- use __name__"
    recommendation_template = (
        "logging.getLogger(__name__) lets the logger inherit configuration from its"
        " package and respects the dotted hierarchy. Hardcoded names break that and"
        " make per-module log filtering brittle."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not _is_get_logger_call(node):
                    continue
                if not node.args:
                    continue
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# LOG-004  PrintInsteadOfLog
# ---------------------------------------------------------------

_CLI_LIBRARY_TOPS: frozenset[str] = frozenset({"click", "typer", "argparse", "fire"})
_CLI_FILE_NAMES: frozenset[str] = frozenset({"cli.py", "__main__.py"})


def _is_cli_or_test_file(fi: FileInfo) -> bool:
    rp = fi.relative_path.replace("\\", "/")
    name = rp.rsplit("/", 1)[-1]
    if "test" in rp.lower() or name.startswith("test_") or name.endswith("_test.py"):
        return True
    if name in _CLI_FILE_NAMES:
        return True
    for imp in fi.imports:
        top = imp.split(".")[0]
        if top in _CLI_LIBRARY_TOPS:
            return True
    return False


class PrintInsteadOfLog(Rule):
    """Detect print() calls in non-test, non-CLI Python modules.

    Principles: #13 (The system must explain itself).
    Source: 12-Factor App -- treat logs as event streams; print bypasses level
    filtering, structured fields, and aggregation.
    """

    code = "LOG-004"
    severity = Severity.WARN
    category = Category.LOGGING
    message_template = "print() call at line {line} -- use a logger instead"
    recommendation_template = (
        "Service code should emit log records, not stdout text. Replace print()"
        " with logger.info / logger.debug so the message gains a level, a logger"
        " name, and structured fields the operator can filter on."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            if _is_cli_or_test_file(fi):
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Name) and func.id == "print":
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# LOG-005  NoCorrelationID
# ---------------------------------------------------------------

_ENDPOINT_DECORATOR_ATTRS: frozenset[str] = frozenset(
    {
        "route",
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
        "api_view",
        "action",
    }
)
_ENDPOINT_DECORATOR_NAMES: frozenset[str] = frozenset({"api_view", "action"})
_CORRELATION_KEYS: frozenset[str] = frozenset(
    {"request_id", "correlation_id", "trace_id", "x_request_id"}
)


def _is_endpoint_decorator(dec: ast.expr) -> bool:
    target = dec.func if isinstance(dec, ast.Call) else dec
    if isinstance(target, ast.Attribute):
        return target.attr in _ENDPOINT_DECORATOR_ATTRS
    if isinstance(target, ast.Name):
        return target.id in _ENDPOINT_DECORATOR_NAMES
    return False


def _logger_calls_in_body(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Call]:
    out: list[ast.Call] = []
    for stmt in fn.body:
        for child in ast.walk(stmt):
            if isinstance(child, ast.Call) and _is_logger_call(child):
                out.append(child)
    return out


def _has_correlation_extra(call: ast.Call) -> bool:
    for kw in call.keywords:
        if kw.arg != "extra":
            continue
        value = kw.value
        if isinstance(value, ast.Dict):
            for key in value.keys:
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and key.value in _CORRELATION_KEYS
                ):
                    return True
        else:
            # Variable / call expression -- assume it carries the correlation
            # context to keep this rule from nagging on legitimate patterns.
            return True
    return False


class NoCorrelationID(Rule):
    """Detect endpoint handlers that log without a request/correlation id in extra=.

    Principles: #5 (State must be visible), #13 (The system must explain itself).
    Source: 12-Factor App + OpenTelemetry -- a request that cannot be stitched
    across log lines might as well not have been logged.
    """

    code = "LOG-005"
    severity = Severity.INFO
    category = Category.LOGGING
    message_template = "Endpoint handler logs at line {line} without correlation id in extra="
    recommendation_template = (
        "Pass extra={{'request_id': request_id}} (or correlation_id / trace_id) on"
        " every logger call inside an HTTP handler so log lines from the same"
        " request can be stitched together by ops."
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
                if not any(_is_endpoint_decorator(d) for d in node.decorator_list):
                    continue
                calls = _logger_calls_in_body(node)
                if not calls:
                    continue
                if any(_has_correlation_extra(c) for c in calls):
                    continue
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=calls[0].lineno,
                        function=node.name,
                    )
                )
        return findings


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

LOGGING_RULES = (
    UnstructuredLogging(),
    SensitiveDataInLog(),
    InconsistentLoggerName(),
    PrintInsteadOfLog(),
    NoCorrelationID(),
)
