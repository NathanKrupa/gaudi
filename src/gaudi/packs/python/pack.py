"""
Python language pack for Gaudí.

Registers all Python-specific rules and provides the parser
that extracts structural context from Python projects.
"""

from __future__ import annotations

from pathlib import Path

from gaudi.core import Finding
from gaudi.pack import Pack
from gaudi.packs.python.context import PythonContext
from gaudi.packs.python.parser import parse_project
from gaudi.packs.python.rules import ALL_RULES


class PythonPack(Pack):
    """
    Language pack for Python projects.

    Covers Django, SQLAlchemy, FastAPI, Flask, Celery, Pandas, Requests,
    Pydantic, pytest, DRF, general architecture, and 3.14 compatibility.
    """

    name = "python"
    description = (
        "Full Python stack: Django, FastAPI, SQLAlchemy, Flask, "
        "Celery, Pandas, DRF, and 3.14 compat"
    )
    extensions = (".py",)

    def __init__(self) -> None:
        super().__init__()
        for rule in ALL_RULES:
            self.register_rule(rule)

    def parse(self, path: Path) -> PythonContext:
        """Parse a Python project and return structural context."""
        return parse_project(path)

    def check(self, path: Path) -> list[Finding]:
        """Parse the project, then run only rules whose libraries are detected."""
        context = self.parse(path)
        findings: list[Finding] = []
        for rule in self._rules:
            if rule.requires_library and rule.requires_library not in context.detected_libraries:
                continue
            results = rule.check(context)
            if results:
                findings.extend(results)
        return sorted(findings, key=lambda f: (f.severity.priority, f.code))
