"""
Python project context — the structural information extracted by the parser.

This is what rules operate against. It provides a normalized view of
Django models, SQLAlchemy tables, project structure, etc.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path


class Framework(Enum):
    """Python web frameworks detected by the parser."""

    DJANGO = "django"
    SQLALCHEMY = "sqlalchemy"
    FASTAPI = "fastapi"
    FLASK = "flask"
    UNKNOWN = "unknown"


@dataclass
class ColumnInfo:
    """A database column/field extracted from a model."""

    name: str
    field_type: str  # e.g., "CharField", "ForeignKey", "Integer"
    nullable: bool = False
    has_index: bool = False
    has_unique: bool = False
    is_foreign_key: bool = False
    fk_target: str | None = None
    max_length: int | None = None
    default: str | None = None
    source_line: int = 0
    raw_line: str = ""


@dataclass
class ModelInfo:
    """A database model/table extracted from a Django or SQLAlchemy file."""

    name: str
    source_file: str = ""
    source_line: int = 0
    columns: list[ColumnInfo] = field(default_factory=list)
    has_meta: bool = False
    meta_options: dict = field(default_factory=dict)
    bases: list[str] = field(default_factory=list)
    framework: str = ""  # "django" or "sqlalchemy"

    @property
    def column_names(self) -> set[str]:
        return {c.name for c in self.columns}

    def has_column(self, name: str) -> bool:
        return name in self.column_names

    @property
    def foreign_keys(self) -> list[ColumnInfo]:
        return [c for c in self.columns if c.is_foreign_key]

    @property
    def nullable_foreign_keys(self) -> list[ColumnInfo]:
        return [c for c in self.foreign_keys if c.nullable]

    @property
    def unindexed_columns(self) -> list[ColumnInfo]:
        return [
            c for c in self.columns if not c.has_index and not c.has_unique and not c.is_foreign_key
        ]


@dataclass
class FileInfo:
    """Metadata about a Python source file."""

    path: Path
    relative_path: str
    source: str = ""
    line_count: int = 0
    imports: list[str] = field(default_factory=list)
    has_models: bool = False

    def has_import(self, name: str) -> bool:
        """Check if this file imports a module containing the given name."""
        return any(name in imp for imp in self.imports)

    @cached_property
    def ast_tree(self) -> ast.Module | None:
        """Parsed AST, cached across all rules. Returns None on SyntaxError."""
        if not self.source:
            return None
        try:
            return ast.parse(self.source)
        except SyntaxError:
            return None


@dataclass
class PythonContext:
    """
    Complete structural context for a Python project.

    This is the object that all Python pack rules receive in their check() method.
    """

    root: Path
    models: list[ModelInfo] = field(default_factory=list)
    files: list[FileInfo] = field(default_factory=list)
    framework: Framework = Framework.UNKNOWN
    has_settings: bool = False
    has_requirements: bool = False
    has_pyproject: bool = False
    detected_libraries: set[str] = field(default_factory=set)
    # The architectural school this project has declared in gaudi.toml.
    # Defaults to "classical" when unset, matching the engine default.
    school: str = "classical"

    @property
    def model_names(self) -> set[str]:
        return {m.name for m in self.models}

    def file_for_model(self, model: ModelInfo) -> FileInfo | None:
        """Look up the FileInfo for a model's source file."""
        return next((f for f in self.files if f.relative_path == model.source_file), None)
