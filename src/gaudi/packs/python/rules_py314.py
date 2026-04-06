"""
Python 3.14 compatibility rules for Gaudí.

Detects usage of APIs removed or deprecated in Python 3.14, and flags
patterns that need attention when targeting 3.14+.

Reference: https://docs.python.org/3.14/whatsnew/3.14.html
"""

from __future__ import annotations

import ast

from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------------------
# Removed in 3.14
# ---------------------------------------------------------------------------

# Map of removed imports: module -> list of (name, replacement)
REMOVED_IN_314 = {
    "argparse": [
        ("BooleanOptionalAction.type", "Remove the type parameter from BooleanOptionalAction"),
        (
            "BooleanOptionalAction.choices",
            "Remove the choices parameter from BooleanOptionalAction",
        ),
        (
            "BooleanOptionalAction.metavar",
            "Remove the metavar parameter from BooleanOptionalAction",
        ),
    ],
    "ast": [
        ("Num", "Use ast.Constant instead"),
        ("Str", "Use ast.Constant instead"),
        ("Bytes", "Use ast.Constant instead"),
        ("NameConstant", "Use ast.Constant instead"),
        ("Ellipsis", "Use ast.Constant instead"),
        ("Attribute.value.n", "Use ast.Constant.value instead"),
        ("Attribute.value.s", "Use ast.Constant.value instead"),
    ],
    "asyncio": [
        ("MultiLoopChildWatcher", "Use the default child watcher"),
        ("FastChildWatcher", "Use the default child watcher"),
        ("AbstractChildWatcher", "Use the default child watcher"),
        ("SafeChildWatcher", "Use the default child watcher"),
        ("set_child_watcher", "Child watchers are no longer needed in 3.14"),
        ("get_child_watcher", "Child watchers are no longer needed in 3.14"),
    ],
    "email.utils": [
        ("localtime.isdst", "The isdst parameter has been removed from email.utils.localtime()"),
    ],
    "importlib.abc": [
        ("ResourceReader", "Use importlib.resources.abc.TraversableResources instead"),
    ],
    "itertools": [
        ("__copy__", "copy/deepcopy/pickle support removed from itertools objects"),
    ],
    "pathlib": [
        ("PurePath.is_reserved", "Use os.path.isreserved() instead"),
    ],
    "pkgutil": [
        ("find_loader", "Use importlib.util.find_spec() instead"),
        ("get_loader", "Use importlib.util.find_spec() instead"),
    ],
    "sqlite3": [
        (
            "version",
            "sqlite3.version (module version string) has been removed; use sqlite3.sqlite_version for the SQLite library version",
        ),
        (
            "version_info",
            "sqlite3.version_info has been removed; use sqlite3.sqlite_version_info instead",
        ),
    ],
    "urllib.parse": [
        ("Quoter", "urllib.parse.Quoter was never a public API and has been removed"),
    ],
}

# Simple lookup: deprecated module-level names that can be detected via import
REMOVED_IMPORT_NAMES = {
    # ast node types removed
    ("ast", "Num"): "Use ast.Constant instead of ast.Num",
    ("ast", "Str"): "Use ast.Constant instead of ast.Str",
    ("ast", "Bytes"): "Use ast.Constant instead of ast.Bytes",
    ("ast", "NameConstant"): "Use ast.Constant instead of ast.NameConstant",
    ("ast", "Ellipsis"): "Use ast.Constant instead of ast.Ellipsis",
    # asyncio child watchers
    (
        "asyncio",
        "MultiLoopChildWatcher",
    ): "Child watchers removed in 3.14; use the default child watcher",
    (
        "asyncio",
        "FastChildWatcher",
    ): "Child watchers removed in 3.14; use the default child watcher",
    (
        "asyncio",
        "AbstractChildWatcher",
    ): "Child watchers removed in 3.14; use the default child watcher",
    (
        "asyncio",
        "SafeChildWatcher",
    ): "Child watchers removed in 3.14; use the default child watcher",
    ("asyncio", "set_child_watcher"): "Child watchers removed in 3.14",
    ("asyncio", "get_child_watcher"): "Child watchers removed in 3.14",
    # pkgutil
    ("pkgutil", "find_loader"): "Use importlib.util.find_spec() instead",
    ("pkgutil", "get_loader"): "Use importlib.util.find_spec() instead",
    # sqlite3
    ("sqlite3", "version"): "sqlite3.version removed in 3.14; use sqlite3.sqlite_version",
    (
        "sqlite3",
        "version_info",
    ): "sqlite3.version_info removed in 3.14; use sqlite3.sqlite_version_info",
}

# Deprecated modules (pty was deprecated, scheduled for future removal)
DEPRECATED_MODULES = {
    "pty": "The pty module is deprecated; consider using a third-party library",
}

# Deprecated in 3.14, pending removal in 3.15+
DEPRECATED_IN_314 = {
    (
        "asyncio",
        "iscoroutinefunction",
    ): "Deprecated in 3.14, removed in 3.16; use inspect.iscoroutinefunction() instead",
    (
        "locale",
        "getdefaultlocale",
    ): "Deprecated since 3.11, removal in 3.15; use getlocale(), setlocale(), and getencoding()",
    ("pathlib", "PurePath.is_reserved"): "Deprecated in 3.13; use os.path.isreserved() instead",
}


class RemovedIn314Import(Rule):
    """
    PY314-001: Import of API removed in Python 3.14.

    Detects `from module import name` or `import module.name` patterns
    that reference APIs removed in Python 3.14.
    """

    code = "PY314-001"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "'{name}' from '{module}' was removed in Python 3.14"
    recommendation_template = "{replacement}"

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for file_info in context.files:
            try:
                source = file_info.path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except (SyntaxError, Exception):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for alias in node.names:
                        key = (node.module, alias.name)
                        if key in REMOVED_IMPORT_NAMES:
                            findings.append(
                                self.finding(
                                    file=file_info.relative_path,
                                    line=node.lineno,
                                    name=alias.name,
                                    module=node.module,
                                    replacement=REMOVED_IMPORT_NAMES[key],
                                )
                            )
        return findings


class DeprecatedIn314Import(Rule):
    """
    PY314-002: Import of API deprecated in Python 3.14.

    These APIs still work but will be removed in a future Python version.
    """

    code = "PY314-002"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "'{name}' from '{module}' is deprecated as of Python 3.14"
    recommendation_template = "{replacement}"

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for file_info in context.files:
            try:
                source = file_info.path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except (SyntaxError, Exception):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    for alias in node.names:
                        key = (node.module, alias.name)
                        if key in DEPRECATED_IN_314:
                            findings.append(
                                self.finding(
                                    file=file_info.relative_path,
                                    line=node.lineno,
                                    name=alias.name,
                                    module=node.module,
                                    replacement=DEPRECATED_IN_314[key],
                                )
                            )

                # Check for deprecated module imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in DEPRECATED_MODULES:
                            findings.append(
                                self.finding(
                                    file=file_info.relative_path,
                                    line=node.lineno,
                                    name=alias.name,
                                    module=alias.name,
                                    replacement=DEPRECATED_MODULES[alias.name],
                                )
                            )
                elif isinstance(node, ast.ImportFrom) and node.module in DEPRECATED_MODULES:
                    findings.append(
                        self.finding(
                            file=file_info.relative_path,
                            line=node.lineno,
                            name=node.module,
                            module=node.module,
                            replacement=DEPRECATED_MODULES[node.module],
                        )
                    )
        return findings


class DeferredAnnotationAccess(Rule):
    """
    PY314-003: Direct access to __annotations__ without annotationlib.

    In Python 3.14, annotations are no longer evaluated eagerly (PEP 649/749).
    Code that directly accesses `__annotations__` may get unexpected results.
    Use annotationlib.get_annotations() instead.
    """

    code = "PY314-003"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = (
        "Direct access to '__annotations__' in '{file}' — "
        "annotations are deferred in Python 3.14 (PEP 649)"
    )
    recommendation_template = (
        "Use annotationlib.get_annotations() or typing.get_type_hints() instead of "
        "directly accessing __annotations__. Deferred annotations may not be evaluated yet."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for file_info in context.files:
            try:
                source = file_info.path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except (SyntaxError, Exception):
                continue

            for node in ast.walk(tree):
                # Catch obj.__annotations__ attribute access
                if isinstance(node, ast.Attribute) and node.attr == "__annotations__":
                    findings.append(
                        self.finding(
                            file=file_info.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


class FinallyControlFlow(Rule):
    """
    PY314-004: return/break/continue in finally block.

    PEP 765 (Python 3.14) adds SyntaxWarning for control flow statements
    (return, break, continue) inside finally blocks, as these silently
    swallow exceptions. Will become SyntaxError in a future version.
    """

    code = "PY314-004"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = (
        "'{statement}' inside a finally block at line {line} — "
        "this silently swallows exceptions and triggers SyntaxWarning in 3.14"
    )
    recommendation_template = (
        "Move the {statement} statement outside the finally block. "
        "Control flow in finally blocks will become a SyntaxError in a future Python version."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for file_info in context.files:
            try:
                source = file_info.path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except (SyntaxError, Exception):
                continue

            findings.extend(self._check_node(tree, file_info.relative_path))
        return findings

    def _check_node(self, tree: ast.AST, filepath: str) -> list[Finding]:
        findings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Try) and node.finalbody:
                for stmt in ast.walk(ast.Module(body=node.finalbody, type_ignores=[])):
                    if isinstance(stmt, ast.Return):
                        findings.append(
                            self.finding(
                                file=filepath,
                                line=stmt.lineno,
                                statement="return",
                            )
                        )
                    elif isinstance(stmt, ast.Break):
                        findings.append(
                            self.finding(
                                file=filepath,
                                line=stmt.lineno,
                                statement="break",
                            )
                        )
                    elif isinstance(stmt, ast.Continue):
                        findings.append(
                            self.finding(
                                file=filepath,
                                line=stmt.lineno,
                                statement="continue",
                            )
                        )
        return findings


class NotImplementedBoolContext(Rule):
    """
    PY314-005: Using NotImplemented in a boolean context.

    In Python 3.14, using NotImplemented in a boolean context raises
    TypeError (previously DeprecationWarning since 3.9).
    """

    code = "PY314-005"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = (
        "Possible use of NotImplemented in boolean context at line {line} — "
        "this raises TypeError in Python 3.14"
    )
    recommendation_template = (
        "Return NotImplemented from special methods to signal the operation is not supported, "
        "but never use it in if/while conditions or bool() calls. Use 'is NotImplemented' for checks."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for file_info in context.files:
            try:
                source = file_info.path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except (SyntaxError, Exception):
                continue

            for node in ast.walk(tree):
                # Catch: if NotImplemented, while NotImplemented, bool(NotImplemented)
                if isinstance(node, (ast.If, ast.While)):
                    if self._is_not_implemented(node.test):
                        findings.append(
                            self.finding(
                                file=file_info.relative_path,
                                line=node.lineno,
                            )
                        )
        return findings

    def _is_not_implemented(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Name) and node.id == "NotImplemented":
            return True
        return False


class TarfileNoFilter(Rule):
    """
    PY314-006: tarfile.extract/extractall without filter parameter.

    In Python 3.14, the default tarfile extraction filter changed to 'data'.
    Code that extracts tar archives without specifying a filter should
    explicitly set filter='data' or filter='fully_trusted'.
    """

    code = "PY314-006"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = (
        "tarfile extract/extractall call without explicit filter parameter at line {line} — "
        "the default changed to 'data' in Python 3.14"
    )
    recommendation_template = (
        "Add filter='data' (safe default) or filter='fully_trusted' (old behavior) "
        "to tarfile.extract() and tarfile.extractall() calls."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings = []
        for file_info in context.files:
            if "tarfile" not in str(file_info.path):
                # Quick check: only parse files that might use tarfile
                try:
                    source = file_info.path.read_text(encoding="utf-8", errors="replace")
                    if "tarfile" not in source:
                        continue
                except Exception:
                    continue

            try:
                source = file_info.path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except (SyntaxError, Exception):
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func_name = self._get_call_name(node)
                    if func_name and func_name.endswith((".extract", ".extractall")):
                        # Check if 'filter' is in keyword arguments
                        has_filter = any(kw.arg == "filter" for kw in node.keywords)
                        if not has_filter:
                            findings.append(
                                self.finding(
                                    file=file_info.relative_path,
                                    line=node.lineno,
                                )
                            )
        return findings

    def _get_call_name(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Attribute):
            return f".{node.func.attr}"
        if isinstance(node.func, ast.Name):
            return node.func.id
        return None


# ---------------------------------------------------------------------------
# Rule registry for Python 3.14
# ---------------------------------------------------------------------------

PY314_RULES = [
    RemovedIn314Import(),
    DeprecatedIn314Import(),
    DeferredAnnotationAccess(),
    FinallyControlFlow(),
    NotImplementedBoolContext(),
    TarfileNoFilter(),
]
