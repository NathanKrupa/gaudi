"""
Python project parser.

Extracts structural information from Django models, SQLAlchemy tables,
and general Python project layout using AST parsing.
"""

from __future__ import annotations

import ast
from pathlib import Path

from gaudi.packs.python.context import (
    ColumnInfo,
    FileInfo,
    Framework,
    ModelInfo,
    PythonContext,
)

# Maps import prefixes to library activation keys
_IMPORT_TO_LIBRARY: dict[str, str] = {
    "django": "django",
    "rest_framework": "drf",
    "fastapi": "fastapi",
    "sqlalchemy": "sqlalchemy",
    "flask": "flask",
    "celery": "celery",
    "pandas": "pandas",
    "requests": "requests",
    "httpx": "requests",
    "pydantic": "pydantic",
    "pytest": "pytest",
    "boto3": "boto3",
    "botocore": "boto3",
    "anthropic": "anthropic",
}

# Maps PyPI package names to library activation keys
_PACKAGE_TO_LIBRARY: dict[str, str] = {
    "django": "django",
    "djangorestframework": "drf",
    "fastapi": "fastapi",
    "sqlalchemy": "sqlalchemy",
    "flask": "flask",
    "celery": "celery",
    "pandas": "pandas",
    "requests": "requests",
    "httpx": "requests",
    "pydantic": "pydantic",
    "pytest": "pytest",
    "boto3": "boto3",
    "anthropic": "anthropic",
}

# Django field types that map to database columns
DJANGO_FIELD_TYPES = frozenset(
    {
        "AutoField",
        "BigAutoField",
        "SmallAutoField",
        "BooleanField",
        "NullBooleanField",
        "CharField",
        "SlugField",
        "URLField",
        "EmailField",
        "FilePathField",
        "TextField",
        "IntegerField",
        "SmallIntegerField",
        "BigIntegerField",
        "PositiveIntegerField",
        "PositiveSmallIntegerField",
        "PositiveBigIntegerField",
        "FloatField",
        "DecimalField",
        "DateField",
        "DateTimeField",
        "TimeField",
        "DurationField",
        "FileField",
        "ImageField",
        "BinaryField",
        "UUIDField",
        "GenericIPAddressField",
        "IPAddressField",
        "JSONField",
        "ForeignKey",
        "OneToOneField",
        "ManyToManyField",
    }
)

# Patterns for detecting frameworks
DJANGO_IMPORTS = frozenset({"django.db", "django.db.models", "models.Model"})
SQLALCHEMY_IMPORTS = frozenset({"sqlalchemy", "sqlalchemy.orm"})


def parse_project(path: Path) -> PythonContext:
    """
    Parse a Python project and extract structural information.

    Handles both single files and directories.
    """
    root = path if path.is_dir() else path.parent
    context = PythonContext(root=root)

    if path.is_file():
        py_files = [path]
    else:
        py_files = sorted(path.rglob("*.py"))
        # Filter out common non-project directories
        exclude_dirs = {
            "venv",
            ".venv",
            "env",
            ".env",
            "node_modules",
            "__pycache__",
            ".git",
            "migrations",
        }
        py_files = [f for f in py_files if not any(part in exclude_dirs for part in f.parts)]

    # Detect project-level files
    if path.is_dir():
        context.has_settings = (path / "settings.py").exists() or any(
            f.name == "settings.py" for f in py_files
        )
        context.has_requirements = (path / "requirements.txt").exists()
        context.has_pyproject = (path / "pyproject.toml").exists()

    # Parse each file
    for py_file in py_files:
        file_info = _parse_file(py_file, root)
        context.files.append(file_info)

        # Detect framework from imports
        for imp in file_info.imports:
            if any(d in imp for d in DJANGO_IMPORTS):
                context.framework = Framework.DJANGO
            elif any(s in imp for s in SQLALCHEMY_IMPORTS):
                if context.framework != Framework.DJANGO:
                    context.framework = Framework.SQLALCHEMY

        # Extract models if this looks like a models file
        if file_info.has_models:
            fw = context.framework if context.framework != Framework.UNKNOWN else Framework.DJANGO
            models = _extract_models(py_file, root, fw.value)
            context.models.extend(models)

    context.detected_libraries = _detect_libraries(root, context.files)
    return context


def _detect_libraries(root: Path, files: list[FileInfo]) -> set[str]:
    """Detect which libraries a project uses from dependencies and imports."""
    libraries: set[str] = set()

    # 1. Check pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")
            for pkg_name, lib_key in _PACKAGE_TO_LIBRARY.items():
                if pkg_name in text.lower():
                    libraries.add(lib_key)
        except Exception:
            pass

    # 2. Check requirements*.txt files
    for req_file in root.glob("requirements*.txt"):
        try:
            for line in req_file.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip().lower()
                if not line or line.startswith("#") or line.startswith("-"):
                    continue
                # Strip version specifiers: "django>=4.2" -> "django"
                pkg = (
                    line.split("==")[0]
                    .split(">=")[0]
                    .split("<=")[0]
                    .split("~=")[0]
                    .split("!=")[0]
                    .split("[")[0]
                    .strip()
                )
                if pkg in _PACKAGE_TO_LIBRARY:
                    libraries.add(_PACKAGE_TO_LIBRARY[pkg])
        except Exception:
            pass

    # 3. Fall back to import scanning (catches cases with no dependency files)
    for fi in files:
        for imp in fi.imports:
            top_module = imp.split(".")[0]
            if top_module in _IMPORT_TO_LIBRARY:
                libraries.add(_IMPORT_TO_LIBRARY[top_module])

    return libraries


def _parse_file(filepath: Path, root: Path) -> FileInfo:
    """Parse a single Python file for metadata."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return FileInfo(path=filepath, relative_path=str(filepath.relative_to(root)))

    file_info = FileInfo(
        path=filepath,
        relative_path=str(filepath.relative_to(root)),
        source=source,
        line_count=source.count("\n") + 1,
    )

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return file_info

    # Extract imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                file_info.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                file_info.imports.append(node.module)

    # Check if this file contains model definitions
    has_django = any("django" in imp or "models" in imp for imp in file_info.imports)
    has_sqlalchemy = any("sqlalchemy" in imp for imp in file_info.imports)

    if has_django or has_sqlalchemy:
        # Look for class definitions that inherit from model bases
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = _get_name(base)
                    if base_name and any(
                        keyword in base_name for keyword in ["Model", "Base", "DeclarativeBase"]
                    ):
                        file_info.has_models = True
                        break

    return file_info


def _extract_models(filepath: Path, root: Path, framework: str) -> list[ModelInfo]:
    """Extract model/table definitions from a Python file."""
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
    except (SyntaxError, Exception):
        return []

    source_lines = source.splitlines()
    models = []
    relative_path = str(filepath.relative_to(root))

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        bases = [_get_name(b) for b in node.bases]
        bases = [b for b in bases if b]

        # Check if this is a model class
        is_model = any(
            keyword in base
            for base in bases
            for keyword in ["Model", "models.Model", "Base", "DeclarativeBase"]
        )

        if not is_model:
            continue

        model = ModelInfo(
            name=node.name,
            source_file=relative_path,
            source_line=node.lineno,
            bases=bases,
            framework=framework,
        )

        # Extract fields/columns
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        col = _parse_field_assignment(
                            target.id, item.value, item.lineno, source_lines
                        )
                        if col:
                            model.columns.append(col)

            elif isinstance(item, ast.AnnAssign) and item.target:
                if isinstance(item.target, ast.Name) and item.value:
                    col = _parse_field_assignment(
                        item.target.id, item.value, item.lineno, source_lines
                    )
                    if col:
                        model.columns.append(col)

            # Check for Meta class
            elif isinstance(item, ast.ClassDef) and item.name == "Meta":
                model.has_meta = True
                for meta_item in item.body:
                    if isinstance(meta_item, ast.Assign):
                        for target in meta_item.targets:
                            if isinstance(target, ast.Name):
                                model.meta_options[target.id] = True

        models.append(model)

    return models


def _parse_field_assignment(
    name: str,
    value: ast.expr,
    lineno: int,
    source_lines: list[str],
) -> ColumnInfo | None:
    """Parse a field assignment to extract column information."""
    if not isinstance(value, ast.Call):
        return None

    func_name = _get_name(value.func)
    if not func_name:
        return None

    # Strip module prefix (models.CharField -> CharField)
    short_name = func_name.split(".")[-1]

    if short_name not in DJANGO_FIELD_TYPES:
        return None

    raw_line = source_lines[lineno - 1] if lineno <= len(source_lines) else ""

    col = ColumnInfo(
        name=name,
        field_type=short_name,
        source_line=lineno,
        raw_line=raw_line.strip(),
        is_foreign_key=short_name in {"ForeignKey", "OneToOneField"},
    )

    # Parse keyword arguments
    for kw in value.keywords:
        if kw.arg == "null" and isinstance(kw.value, ast.Constant):
            col.nullable = bool(kw.value.value)
        elif kw.arg == "db_index" and isinstance(kw.value, ast.Constant):
            col.has_index = bool(kw.value.value)
        elif kw.arg == "unique" and isinstance(kw.value, ast.Constant):
            col.has_unique = bool(kw.value.value)
        elif kw.arg == "max_length" and isinstance(kw.value, ast.Constant):
            col.max_length = kw.value.value
        elif kw.arg == "default":
            col.default = ast.dump(kw.value)

    # ForeignKey target
    if col.is_foreign_key and value.args:
        col.fk_target = _get_name(value.args[0])
        # Django ForeignKeys get auto-indexed
        col.has_index = True

    return col


def _get_name(node: ast.expr) -> str | None:
    """Extract a dotted name from an AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        parent = _get_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None
