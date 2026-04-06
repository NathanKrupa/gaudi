"""
ABOUTME: Architecture 90 curriculum rules for structural design checks.
ABOUTME: Covers project shape, layers, config, types, errors, logging, ops.
"""

from __future__ import annotations

import ast
import re
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# STRUCT-010  PathHacks
# ---------------------------------------------------------------


class PathHacks(Rule):
    code = "STRUCT-010"
    severity = Severity.ERROR
    category = Category.STRUCTURE
    message_template = "sys.path manipulation at line {line}"
    recommendation_template = (
        "Use proper packaging (pyproject.toml + pip install -e .) instead of sys.path hacks."
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
                if func.attr not in ("insert", "append"):
                    continue
                val = func.value
                if (
                    isinstance(val, ast.Attribute)
                    and val.attr == "path"
                    and isinstance(val.value, ast.Name)
                    and val.value.id == "sys"
                ):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# STRUCT-011  MissingPyproject
# ---------------------------------------------------------------


class MissingPyproject(Rule):
    code = "STRUCT-011"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "Project has no pyproject.toml"
    recommendation_template = (
        "Add a pyproject.toml for modern Python packaging,"
        " dependency management, and tool configuration."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        if not (context.root / "pyproject.toml").exists():
            return [self.finding()]
        return []


# ---------------------------------------------------------------
# STRUCT-012  NoEntryPoint
# ---------------------------------------------------------------


class NoEntryPoint(Rule):
    code = "STRUCT-012"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "Script '{file}' has CLI logic but no entry point in pyproject.toml"
    recommendation_template = (
        "Register this script as a console_scripts entry point in pyproject.toml."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            has_cli_import = False
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in ("argparse", "click"):
                            has_cli_import = True
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.split(".")[0] in ("argparse", "click"):
                        has_cli_import = True
            if not has_cli_import:
                continue
            has_main_guard = False
            for node in ast.walk(tree):
                if not isinstance(node, ast.If):
                    continue
                test = node.test
                if isinstance(test, ast.Compare):
                    left = test.left
                    if (
                        isinstance(left, ast.Name)
                        and left.id == "__name__"
                        and test.comparators
                        and isinstance(test.comparators[0], ast.Constant)
                        and test.comparators[0].value == "__main__"
                    ):
                        has_main_guard = True
                        break
            if has_main_guard:
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                    )
                )
        return findings


# ---------------------------------------------------------------
# STRUCT-013  NoLockFile
# ---------------------------------------------------------------

_LOCK_FILES = (
    "requirements-lock.txt",
    "poetry.lock",
    "Pipfile.lock",
    "pdm.lock",
)


class NoLockFile(Rule):
    code = "STRUCT-013"
    severity = Severity.INFO
    category = Category.STRUCTURE
    message_template = "Project has no dependency lock file"
    recommendation_template = (
        "Add a lock file (pip freeze > requirements-lock.txt)"
        " to pin exact dependency versions"
        " for reproducible builds."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        root = context.root
        for name in _LOCK_FILES:
            if (root / name).exists():
                return []
        return [self.finding()]


# ---------------------------------------------------------------
# ARCH-010  ImportDirectionViolation
# ---------------------------------------------------------------

_OUTER_KEYWORDS = ("scripts.", "cli.", "commands.", "views.")


class ImportDirectionViolation(Rule):
    code = "ARCH-010"
    severity = Severity.ERROR
    category = Category.ARCHITECTURE
    message_template = "Inner-layer file imports from outer layer: '{imported}' at line {line}"
    recommendation_template = (
        "Import direction should flow inward only."
        " Outer imports middle, middle imports inner."
        " Never reverse."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                mod_name: str | None = None
                lineno = 0
                if isinstance(node, ast.ImportFrom):
                    mod_name = node.module
                    lineno = node.lineno
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(alias.name.startswith(k) for k in _OUTER_KEYWORDS):
                            findings.append(
                                self.finding(
                                    file=fi.relative_path,
                                    line=node.lineno,
                                    imported=alias.name,
                                )
                            )
                    continue
                if mod_name and any(mod_name.startswith(k) for k in _OUTER_KEYWORDS):
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=lineno,
                            imported=mod_name,
                        )
                    )
        return findings


# ---------------------------------------------------------------
# ARCH-011  ConnectorLogicLeak
# ---------------------------------------------------------------

_DATA_LAYER_KEYWORDS = ("connector", "store", "repository", "db")


class ConnectorLogicLeak(Rule):
    code = "ARCH-011"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Business logic (if/elif) in data-layer file '{file}' at line {line}"
    recommendation_template = (
        "Connectors should only talk to external systems."
        " Move decision-making to the service layer."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            path_lower = fi.relative_path.lower()
            is_data_layer = any(kw in path_lower for kw in _DATA_LAYER_KEYWORDS)
            if not is_data_layer:
                continue
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for child in ast.walk(node):
                    if isinstance(child, ast.If) and child.orelse:
                        findings.append(
                            self.finding(
                                file=fi.relative_path,
                                line=child.lineno,
                            )
                        )
                        break
        return findings


# ---------------------------------------------------------------
# ARCH-013  FatScript
# ---------------------------------------------------------------


class FatScript(Rule):
    code = "ARCH-013"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Entry point '{function}' has {lines} lines of business logic"
    recommendation_template = (
        "Entry points should be thin — parse input,"
        " call a service, format output."
        " Move logic to service functions."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            source_lines = fi.source.splitlines()
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                if not self._is_entry_point(node, fi.source):
                    continue
                body_lines = self._count_logic_lines(node, source_lines)
                if body_lines > 15:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            line=node.lineno,
                            function=node.name,
                            lines=body_lines,
                        )
                    )
        return findings

    @staticmethod
    def _is_entry_point(func: ast.FunctionDef, source: str) -> bool:
        for dec in func.decorator_list:
            name = ""
            if isinstance(dec, ast.Attribute):
                name = dec.attr
            elif isinstance(dec, ast.Name):
                name = dec.id
            elif isinstance(dec, ast.Call):
                if isinstance(dec.func, ast.Attribute):
                    name = dec.func.attr
                elif isinstance(dec.func, ast.Name):
                    name = dec.func.id
            if name in ("command", "group"):
                return True
        if "argparse" in source:
            for child in ast.walk(func):
                if isinstance(child, ast.Attribute):
                    if child.attr in (
                        "ArgumentParser",
                        "add_argument",
                        "parse_args",
                    ):
                        return True
        return False

    @staticmethod
    def _count_logic_lines(
        func: ast.FunctionDef,
        source_lines: list[str],
    ) -> int:
        if not func.body:
            return 0
        start = func.body[0].lineno
        end = func.end_lineno or start
        count = 0
        for i in range(start - 1, end):
            if i >= len(source_lines):
                break
            line = source_lines[i].strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            if line.startswith('"""') or line.startswith("'''"):
                continue
            if line.startswith("@"):
                continue
            count += 1
        return count


# ---------------------------------------------------------------
# ARCH-020  EnvLeakage
# ---------------------------------------------------------------


class EnvLeakage(Rule):
    code = "ARCH-020"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "Class method '{method}' reads environment directly at line {line}"
    recommendation_template = (
        "Accept configuration through __init__ parameters."
        " Only factory functions should read os.getenv()."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                for item in node.body:
                    if not isinstance(
                        item,
                        (ast.FunctionDef, ast.AsyncFunctionDef),
                    ):
                        continue
                    method_name = item.name
                    for child in ast.walk(item):
                        if self._is_env_read(child):
                            findings.append(
                                self.finding(
                                    file=fi.relative_path,
                                    line=child.lineno,
                                    method=method_name,
                                )
                            )
        return findings

    @staticmethod
    def _is_env_read(node: ast.AST) -> bool:
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if (
                    func.attr == "getenv"
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "os"
                ):
                    return True
                if func.attr == "get" and isinstance(func.value, ast.Attribute):
                    inner = func.value
                    if (
                        inner.attr == "environ"
                        and isinstance(inner.value, ast.Name)
                        and inner.value.id == "os"
                    ):
                        return True
        if isinstance(node, ast.Subscript):
            val = node.value
            if (
                isinstance(val, ast.Attribute)
                and val.attr == "environ"
                and isinstance(val.value, ast.Name)
                and val.value.id == "os"
            ):
                return True
        return False


# ---------------------------------------------------------------
# ARCH-022  ScatteredConfig
# ---------------------------------------------------------------


class ScatteredConfig(Rule):
    code = "ARCH-022"
    severity = Severity.WARN
    category = Category.ARCHITECTURE
    message_template = "os.getenv()/os.environ used in {count} files — configuration is scattered"
    recommendation_template = (
        "Centralize configuration reading"
        " in a single module. Other modules should"
        " receive config via parameters."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        files_with_env = sum(
            1 for fi in context.files if re.search(r"os\.(getenv|environ)", fi.source)
        )
        if files_with_env >= 4:
            return [self.finding(count=files_with_env)]
        return []


# ---------------------------------------------------------------
# STRUCT-020  MissingReturnTypes
# ---------------------------------------------------------------


class MissingReturnTypes(Rule):
    code = "STRUCT-020"
    severity = Severity.INFO
    category = Category.STRUCTURE
    message_template = "Public function '{function}' has no return type annotation"
    recommendation_template = (
        "Add return type annotations to public functions"
        " for documentation and type-checker support."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            for node in ast.iter_child_nodes(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                if node.name.startswith("_"):
                    continue
                if node.returns is not None:
                    continue
                if not self._has_return(node):
                    continue
                findings.append(
                    self.finding(
                        file=fi.relative_path,
                        line=node.lineno,
                        function=node.name,
                    )
                )
        return findings

    @staticmethod
    def _has_return(func: ast.FunctionDef) -> bool:
        for child in ast.walk(func):
            if isinstance(child, ast.Return) and (child.value is not None):
                return True
        return False


# ---------------------------------------------------------------
# STRUCT-021  MagicStrings
# ---------------------------------------------------------------

_EXEMPT_STRINGS = frozenset(
    {
        "utf-8",
        "utf8",
        "replace",
        "strict",
        "ignore",
        "ascii",
        "latin-1",
    }
)


class MagicStrings(Rule):
    code = "STRUCT-021"
    severity = Severity.WARN
    category = Category.STRUCTURE
    message_template = "String '{value}' appears {count} times — consider using a constant"
    recommendation_template = "Extract repeated string literals into named constants or enums."

    def check(self, context: PythonContext) -> list[Finding]:
        findings: list[Finding] = []
        for fi in context.files:
            tree = fi.ast_tree
            if tree is None:
                continue
            docstrings = self._collect_docstrings(tree)
            counts: dict[str, int] = {}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant):
                    continue
                if not isinstance(node.value, str):
                    continue
                val = node.value
                if len(val) <= 1 or not val:
                    continue
                if val.lower() in _EXEMPT_STRINGS:
                    continue
                if id(node) in docstrings:
                    continue
                counts[val] = counts.get(val, 0) + 1
            for val, cnt in counts.items():
                if cnt >= 3:
                    findings.append(
                        self.finding(
                            file=fi.relative_path,
                            value=val,
                            count=cnt,
                        )
                    )
        return findings

    @staticmethod
    def _collect_docstrings(
        tree: ast.Module,
    ) -> set[int]:
        ids: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(
                node,
                (
                    ast.Module,
                    ast.ClassDef,
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            ):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    ids.add(id(node.body[0].value))
        return ids


# ---------------------------------------------------------------
# ERR-001  BareExcept
# ---------------------------------------------------------------


class BareExcept(Rule):
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
    code = "ERR-003"
    severity = Severity.WARN
    category = Category.ERROR_HANDLING
    message_template = "Error logged but not re-raised at line {line}"
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
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Attribute) and func.attr in ("error", "exception"):
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
# LOG-001  UnstructuredLogging
# ---------------------------------------------------------------

_LOG_METHODS = frozenset(
    {
        "info",
        "warning",
        "debug",
        "error",
    }
)


class UnstructuredLogging(Rule):
    code = "LOG-001"
    severity = Severity.INFO
    category = Category.LOGGING
    message_template = "f-string in logger call at line {line} — use %-formatting"
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
# OPS-002  MissingPrecommit
# ---------------------------------------------------------------


class MissingPrecommit(Rule):
    code = "OPS-002"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no .pre-commit-config.yaml"
    recommendation_template = (
        "Add pre-commit hooks for automated code quality checks before each commit."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        path = context.root / ".pre-commit-config.yaml"
        if not path.exists():
            return [self.finding()]
        return []


# ---------------------------------------------------------------
# OPS-003  MissingPRTemplate
# ---------------------------------------------------------------


class MissingPRTemplate(Rule):
    code = "OPS-003"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no pull request template"
    recommendation_template = (
        "Add .github/PULL_REQUEST_TEMPLATE.md to enforce"
        " consistent PR descriptions with summary, motivation,"
        " and test plan sections."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        paths = [
            context.root / ".github" / "PULL_REQUEST_TEMPLATE.md",
            context.root / ".github" / "pull_request_template.md",
            context.root / "PULL_REQUEST_TEMPLATE.md",
        ]
        if any(p.exists() for p in paths):
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# OPS-004  MissingCodeowners
# ---------------------------------------------------------------


class MissingCodeowners(Rule):
    code = "OPS-004"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no CODEOWNERS file"
    recommendation_template = (
        "Add .github/CODEOWNERS to assign review responsibility."
        " Without it, PRs have no automatic reviewer assignment."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        paths = [
            context.root / ".github" / "CODEOWNERS",
            context.root / "CODEOWNERS",
        ]
        if any(p.exists() for p in paths):
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# OPS-005  MissingContribGuide
# ---------------------------------------------------------------


class MissingContribGuide(Rule):
    code = "OPS-005"
    severity = Severity.INFO
    category = Category.OPERATIONS
    message_template = "Project has no CONTRIBUTING.md"
    recommendation_template = (
        "Add CONTRIBUTING.md documenting the PR workflow, branch naming, and review process."
    )

    def check(self, context: PythonContext) -> list[Finding]:
        paths = [
            context.root / "CONTRIBUTING.md",
            context.root / "contributing.md",
        ]
        if any(p.exists() for p in paths):
            return []
        return [self.finding()]


# ---------------------------------------------------------------
# Exported rule list
# ---------------------------------------------------------------

ARCH90_RULES = (
    PathHacks(),
    MissingPyproject(),
    NoEntryPoint(),
    NoLockFile(),
    ImportDirectionViolation(),
    ConnectorLogicLeak(),
    FatScript(),
    EnvLeakage(),
    ScatteredConfig(),
    MissingReturnTypes(),
    MagicStrings(),
    BareExcept(),
    ErrorSwallowing(),
    UnstructuredLogging(),
    MissingPrecommit(),
    MissingPRTemplate(),
    MissingCodeowners(),
    MissingContribGuide(),
)
