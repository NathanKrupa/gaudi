# ABOUTME: Security fundamental rules for Python (OWASP Top 10 overlap).
# ABOUTME: Detects raw SQL injection, hardcoded credentials, eval/exec, unsafe deserialization, SSRF.
from __future__ import annotations

import ast
import re
from typing import Iterator

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


def _is_test_file(relative_path: str) -> bool:
    """Heuristic: file lives under tests/ or starts with test_."""
    norm = relative_path.replace("\\", "/")
    parts = norm.split("/")
    if any(p == "tests" or p == "test" for p in parts):
        return True
    return parts[-1].startswith("test_")


# ---------------------------------------------------------------
# SEC-002  RawSQLInjection
# ---------------------------------------------------------------

_SQL_EXEC_METHODS = frozenset({"execute", "executemany", "executescript", "raw"})


def _is_unsafe_sql_arg(arg: ast.expr) -> bool:
    """Return True if the SQL string argument is built from interpolation."""
    # f-string
    if isinstance(arg, ast.JoinedStr):
        return True
    # "...".format(...)
    if isinstance(arg, ast.Call):
        func = arg.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == "format"
            and isinstance(func.value, ast.Constant)
            and isinstance(func.value.value, str)
        ):
            return True
    # string concatenation: "..." + var or var + "..."
    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
        left_str = isinstance(arg.left, ast.Constant) and isinstance(arg.left.value, str)
        right_str = isinstance(arg.right, ast.Constant) and isinstance(arg.right.value, str)
        if left_str or right_str:
            return True
    # %-formatting: "..." % var
    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
        if isinstance(arg.left, ast.Constant) and isinstance(arg.left.value, str):
            return True
    return False


class RawSQLInjection(Rule):
    """SEC-002: SQL execution with interpolated strings.

    Principles: #4 (Failure must be named).
    Source: OWASP A03 — Injection: hostile input must be parameterized.
    """

    code = "SEC-002"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = (
        "Interpolated string passed to '{method}' at line {line} — SQL injection risk"
    )
    recommendation_template = (
        "Use parameterized queries: pass values as a separate "
        "tuple/dict argument to execute() instead of formatting "
        "them into the SQL string."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr not in _SQL_EXEC_METHODS:
                    continue
                if not node.args:
                    continue
                if _is_unsafe_sql_arg(node.args[0]):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            method=func.attr,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SEC-003  HardcodedCredential
# ---------------------------------------------------------------

_CREDENTIAL_NAME_PATTERN = re.compile(
    r"(?:^|_)(password|passwd|pwd|secret|api[_-]?key|auth[_-]?token|access[_-]?token|"
    r"private[_-]?key|client[_-]?secret)(?:$|_)",
    re.IGNORECASE,
)
_PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "your-api-key-here",
        "your_api_key_here",
        "changeme",
        "change-me",
        "xxx",
        "todo",
        "fixme",
        "placeholder",
        "example",
    }
)


def _looks_like_credential_name(name: str) -> bool:
    """Match credential-ish identifiers but exclude obvious example/placeholder names."""
    if not _CREDENTIAL_NAME_PATTERN.search(name):
        return False
    lowered = name.lower()
    if "example" in lowered or "placeholder" in lowered or "sample" in lowered:
        return False
    return True


_TEST_PREFIXES = ("test-", "test_", "test.", "fake-", "fake_", "dummy-", "dummy_")


def _looks_like_placeholder_value(value: str) -> bool:
    if value.lower() in _PLACEHOLDER_VALUES:
        return True
    lowered = value.lower()
    if "your-" in lowered or "your_" in lowered:
        return True
    if any(lowered.startswith(prefix) for prefix in _TEST_PREFIXES):
        return True
    return False


class HardcodedCredential(Rule):
    """SEC-003: Credential-named variable assigned to a string literal.

    Principles: #5 (State must be visible), #4 (Failure must be named).
    Source: OWASP A07 — secrets are configuration, not code.
    """

    code = "SEC-003"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = "Hardcoded credential '{name}' at line {line}"
    recommendation_template = (
        "Read secrets from environment variables (os.getenv) or "
        "a secrets manager. Hardcoded credentials leak through git history."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            if _is_test_file(f.relative_path):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                value = node.value
                if not isinstance(value, ast.Constant):
                    continue
                if not isinstance(value.value, str):
                    continue
                if _looks_like_placeholder_value(value.value):
                    continue
                targets: list[ast.expr] = []
                if isinstance(node, ast.Assign):
                    targets = list(node.targets)
                else:
                    targets = [node.target]
                for target in targets:
                    name: str | None = None
                    if isinstance(target, ast.Name):
                        name = target.id
                    elif isinstance(target, ast.Attribute):
                        name = target.attr
                    if name is None:
                        continue
                    if _looks_like_credential_name(name):
                        findings.append(
                            self.finding(
                                file=f.relative_path,
                                line=node.lineno,
                                name=name,
                            )
                        )
        return findings


# ---------------------------------------------------------------
# SEC-004  EvalExecUsage
# ---------------------------------------------------------------


class EvalExecUsage(Rule):
    """SEC-004: Use of built-in eval() or exec().

    Principles: #4 (Failure must be named).
    Source: OWASP A03 — arbitrary code execution from hostile input.
    """

    code = "SEC-004"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = "Call to '{name}' at line {line}"
    recommendation_template = (
        "eval() and exec() execute arbitrary code. Use ast.literal_eval "
        "for safe expression parsing, or refactor to avoid dynamic execution."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            if _is_test_file(f.relative_path):
                continue
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            name=func.id,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# SEC-005  UnsafeDeserialization
# ---------------------------------------------------------------


def _yaml_load_has_safe_loader(call: ast.Call) -> bool:
    """Check if a yaml.load call passes a safe Loader keyword."""
    for kw in call.keywords:
        if kw.arg != "Loader":
            continue
        val = kw.value
        if isinstance(val, ast.Attribute) and "Safe" in val.attr:
            return True
        if isinstance(val, ast.Name) and "Safe" in val.id:
            return True
    return False


class UnsafeDeserialization(Rule):
    """SEC-005: Insecure deserialization via pickle or yaml.load.

    Principles: #4 (Failure must be named).
    Source: OWASP A08 — Software and Data Integrity Failures.
    """

    code = "SEC-005"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = "Unsafe deserialization '{call}' at line {line}"
    recommendation_template = (
        "pickle and yaml.load can execute arbitrary code on untrusted "
        "input. Use json, or yaml.safe_load / Loader=SafeLoader."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if not isinstance(func.value, ast.Name):
                    continue
                module = func.value.id
                attr = func.attr
                # pickle.load / pickle.loads
                if module == "pickle" and attr in ("load", "loads"):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=node.lineno,
                            call=f"pickle.{attr}",
                        )
                    )
                    continue
                # yaml.load without SafeLoader
                if module == "yaml" and attr == "load":
                    if not _yaml_load_has_safe_loader(node):
                        findings.append(
                            self.finding(
                                file=f.relative_path,
                                line=node.lineno,
                                call="yaml.load",
                            )
                        )
        return findings


# ---------------------------------------------------------------
# SEC-006  SSRFVector
# ---------------------------------------------------------------

_HTTP_CALL_TARGETS: dict[str, frozenset[str]] = {
    "requests": frozenset({"get", "post", "put", "delete", "head", "patch"}),
    "httpx": frozenset({"get", "post", "put", "delete", "head", "patch"}),
}

_URLLIB_TARGETS = frozenset({"urlopen"})

_SANITIZER_FUNCS = frozenset({"urlparse", "urlsplit"})

_SANITIZER_METHODS = frozenset({"startswith", "endswith"})


def _is_http_sink(node: ast.Call) -> str | None:
    """Return 'module.method' if the call is a known HTTP sink, else None."""
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    attr = func.attr
    val = func.value
    # requests.get(...), httpx.post(...)
    if isinstance(val, ast.Name) and val.id in _HTTP_CALL_TARGETS:
        if attr in _HTTP_CALL_TARGETS[val.id]:
            return f"{val.id}.{attr}"
    # urllib.request.urlopen(...)
    if (
        isinstance(val, ast.Attribute)
        and isinstance(val.value, ast.Name)
        and val.value.id == "urllib"
        and val.attr == "request"
        and attr in _URLLIB_TARGETS
    ):
        return "urllib.request.urlopen"
    return None


def _url_arg(call: ast.Call) -> ast.expr | None:
    """Extract the URL argument from an HTTP call (first positional or 'url' keyword)."""
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg == "url":
            return kw.value
    return None


def _is_constant_expr(node: ast.expr) -> bool:
    """Return True if the expression is a string constant or an f-string with a constant base."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, ast.JoinedStr):
        # f-string with constant base like f"https://api.example.com/{item_id}"
        # is safe — the base URL is fixed, only path components vary.
        if node.values and isinstance(node.values[0], ast.Constant):
            prefix = node.values[0].value
            if isinstance(prefix, str) and "://" in prefix:
                return True
    return False


def _collect_tainted_names(func_def: ast.FunctionDef) -> set[str]:
    """Walk a function body to find names that carry parameter taint.

    Strategy:
    1. All function parameters are initially tainted.
    2. Simple assignments ``x = tainted`` propagate taint.
    3. If a tainted name passes through a sanitizer (urlparse, startswith,
       ``in`` membership check), clear it.
    """
    tainted: set[str] = set()
    for arg in func_def.args.args:
        tainted.add(arg.arg)

    sanitized: set[str] = set()

    for node in ast.walk(func_def):
        # Detect sanitizers: urlparse(x), x.startswith(...), x in ALLOWED
        if isinstance(node, ast.Call):
            # urlparse(var) / urlsplit(var)
            func = node.func
            callee_name: str | None = None
            if isinstance(func, ast.Name):
                callee_name = func.id
            elif isinstance(func, ast.Attribute):
                callee_name = func.attr
            if callee_name in _SANITIZER_FUNCS and node.args:
                arg0 = node.args[0]
                if isinstance(arg0, ast.Name):
                    sanitized.add(arg0.id)

            # var.startswith(...) / var.endswith(...)
            if (
                isinstance(func, ast.Attribute)
                and func.attr in _SANITIZER_METHODS
                and isinstance(func.value, ast.Name)
            ):
                sanitized.add(func.value.id)

        # Detect ``var in ALLOWED_HOSTS`` or ``var not in ALLOWED``
        if isinstance(node, ast.Compare):
            if isinstance(node.left, ast.Name):
                for op in node.ops:
                    if isinstance(op, (ast.In, ast.NotIn)):
                        sanitized.add(node.left.id)

        # Propagate taint through simple assignment: x = tainted_var
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            value = node.value
            if isinstance(target, ast.Name) and isinstance(value, ast.Name):
                if value.id in tainted and value.id not in sanitized:
                    tainted.add(target.id)
                elif _is_constant_expr(value):
                    pass  # constant assignment, not tainted
            elif isinstance(target, ast.Name) and _is_constant_expr(value):
                pass  # assigning a constant clears taint implicitly (name not added)

    return tainted - sanitized


def _check_function_ssrf(
    func_def: ast.FunctionDef,
    relative_path: str,
) -> Iterator[tuple[int, str]]:
    """Yield (line, sink_name) for HTTP calls with tainted URL args in a function."""
    tainted = _collect_tainted_names(func_def)
    if not tainted:
        return

    for node in ast.walk(func_def):
        if not isinstance(node, ast.Call):
            continue
        sink = _is_http_sink(node)
        if sink is None:
            continue
        url_node = _url_arg(node)
        if url_node is None:
            continue
        if isinstance(url_node, ast.Name) and url_node.id in tainted:
            yield (node.lineno, sink)
        elif isinstance(url_node, ast.Constant):
            pass  # constant URL literal, safe


class SSRFVector(Rule):
    """SEC-006: User input flowing into HTTP calls without validation.

    Principles: #4 (Failure must be named).
    Source: OWASP A10:2021 — Server-Side Request Forgery.

    Uses intra-procedural taint tracking: function parameters are tainted,
    taint propagates through simple assignments, and is cleared by
    urlparse/startswith/membership checks.
    """

    code = "SEC-006"
    severity = Severity.WARN
    category = Category.SECURITY
    message_template = (
        "Tainted URL passed to '{sink}' at line {line} — SSRF risk"
    )
    recommendation_template = (
        "Validate URLs against an allowlist before making HTTP requests. "
        "Use urlparse() to inspect scheme and hostname, and restrict to "
        "known-safe hosts."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for f in context.files:
            tree = f.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for line, sink in _check_function_ssrf(node, f.relative_path):
                    findings.append(
                        self.finding(
                            file=f.relative_path,
                            line=line,
                            sink=sink,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# Exported rule instances
# ---------------------------------------------------------------

SECURITY_RULES = (
    RawSQLInjection(),
    HardcodedCredential(),
    EvalExecUsage(),
    UnsafeDeserialization(),
    SSRFVector(),
)
