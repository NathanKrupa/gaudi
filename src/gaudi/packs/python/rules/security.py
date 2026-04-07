# ABOUTME: Security fundamental rules for Python (OWASP Top 10 overlap).
# ABOUTME: Detects raw SQL injection, hardcoded credentials, eval/exec, unsafe deserialization.
from __future__ import annotations

import ast
import re

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
    """SEC-002: SQL execution with interpolated strings."""

    code = "SEC-002"
    severity = Severity.ERROR
    category = Category.SECURITY
    message_template = "Interpolated string passed to '{method}' at line {line} — SQL injection risk"
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


def _looks_like_placeholder_value(value: str) -> bool:
    if value.lower() in _PLACEHOLDER_VALUES:
        return True
    if "your-" in value.lower() or "your_" in value.lower():
        return True
    return False


class HardcodedCredential(Rule):
    """SEC-003: Credential-named variable assigned to a string literal."""

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
    """SEC-004: Use of built-in eval() or exec()."""

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
    """SEC-005: Insecure deserialization via pickle or yaml.load."""

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
# Exported rule instances
# ---------------------------------------------------------------

SECURITY_RULES = (
    RawSQLInjection(),
    HardcodedCredential(),
    EvalExecUsage(),
    UnsafeDeserialization(),
)
