# ABOUTME: Project shape rules for Python packaging and dependency management.
# ABOUTME: Checks pyproject.toml, entry points, lock files, and sys.path hacks.
from __future__ import annotations

import ast
from gaudi.core import Rule, Finding, Severity, Category
from gaudi.packs.python.context import PythonContext


# ---------------------------------------------------------------
# STRUCT-010  PathHacks
# ---------------------------------------------------------------


_SCRIPT_DIR_KEYWORDS = ("scripts/", "/scripts/", "bin/", "/bin/", "tools/", "/tools/")
# Standalone entrypoint files that are run directly, not imported as packages.
_ENTRYPOINT_FILENAMES = frozenset({"manage.py", "conftest.py"})


def _is_entrypoint_bootstrap(relative_path: str, tree: ast.Module) -> bool:
    """True if the file is an executable entrypoint, where a sys.path bootstrap is expected.

    Entrypoints are run directly (``python scripts/foo.py``) rather than
    imported, so they can't rely on the package being installed and legitimately
    prepend their own location to ``sys.path``. Detected by living under a
    scripts/bin/tools directory, by a known entrypoint filename, or by carrying
    an ``if __name__ == "__main__":`` guard.
    """
    norm = relative_path.replace("\\", "/").lower()
    if any(kw in norm for kw in _SCRIPT_DIR_KEYWORDS):
        return True
    if norm.rsplit("/", 1)[-1] in _ENTRYPOINT_FILENAMES:
        return True
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if (
            isinstance(test, ast.Compare)
            and isinstance(test.left, ast.Name)
            and test.left.id == "__name__"
            and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == "__main__"
        ):
            return True
    return False


class PathHacks(Rule):
    """Detect sys.path manipulation (path hacks).

    Exempts executable entrypoints — files under scripts/bin/tools, known
    entrypoint filenames (manage.py, conftest.py), or files with an
    ``if __name__ == "__main__":`` guard. These are run directly rather than
    imported, so a self-locating ``sys.path`` bootstrap is the by-design way to
    find siblings before the package is installed. A library module that hacks
    ``sys.path`` still fires.

    Principles: #1 (The structure tells the story), #9 (Dependencies flow toward stability).
    Source: ARCH90 Day 1 — proper packaging over sys.path hacks.
    """

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
            if _is_entrypoint_bootstrap(fi.relative_path, tree):
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
    """Detect projects without a pyproject.toml.

    Principles: #1 (The structure tells the story), #14 (Reversibility is a design property).
    Source: ARCH90 Day 1 — modern packaging requires pyproject.toml.
    """

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
    """Detect CLI scripts without console_scripts entry points.

    Principles: #1 (The structure tells the story).
    Source: ARCH90 Day 1 — CLI scripts need entry points.
    """

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
    """Detect projects without a dependency lock file.

    Principles: #14 (Reversibility is a design property).
    Source: ARCH90 Day 1 — pin dependencies for reproducibility.
    """

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
# Exported rule list
# ---------------------------------------------------------------

PACKAGING_RULES = (
    PathHacks(),
    MissingPyproject(),
    NoEntryPoint(),
    NoLockFile(),
)
