"""
Python language pack for Gaudí.

Registers all Python-specific rules and provides the parser
that extracts structural context from Python projects.
"""

from __future__ import annotations

from pathlib import Path

from gaudi.pack import Pack
from gaudi.packs.python.context import PythonContext
from gaudi.packs.python.parser import parse_project
from gaudi.packs.python.rules import ALL_RULES
from gaudi.packs.python.rules_py314 import PY314_RULES
from gaudi.packs.python.rules_libraries import LIBRARY_RULES


class PythonPack(Pack):
    """
    Language pack for Python projects.

    Covers Django, SQLAlchemy, FastAPI, Flask, Celery, Pandas, Requests,
    Pydantic, pytest, DRF, general architecture, and 3.14 compatibility.
    """

    name = "python"
    description = (
        "Full Python stack: Django, FastAPI, SQLAlchemy, Flask, Celery, Pandas, DRF, and 3.14 compat"
    )
    extensions = (".py",)

    def __init__(self) -> None:
        super().__init__()
        for rule in ALL_RULES:
            self.register_rule(rule)
        for rule in PY314_RULES:
            self.register_rule(rule)
        for rule in LIBRARY_RULES:
            self.register_rule(rule)

    def parse(self, path: Path) -> PythonContext:
        """Parse a Python project and return structural context."""
        return parse_project(path)
