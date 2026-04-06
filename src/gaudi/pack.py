"""
Base class for Gaudí language packs.

A language pack teaches Gaudí the architectural patterns and anti-patterns
for a specific language or framework. It provides:

1. A parser that can read project files and extract structural information
2. A set of rules that check for architectural issues
3. A context object that rules operate against
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from gaudi.core import Finding, Rule


class Pack:
    """
    Base class for language packs.

    Subclass this to create a pack for a new language or framework.
    """

    name: str = ""
    description: str = ""
    extensions: list[str] = []  # File extensions this pack handles

    def __init__(self) -> None:
        self._rules: list[Rule] = []

    def register_rule(self, rule: Rule) -> None:
        """Register a rule with this pack."""
        self._rules.append(rule)

    @property
    def rules(self) -> list[Rule]:
        """All registered rules."""
        return list(self._rules)

    def can_handle(self, path: Path) -> bool:
        """Check if this pack can handle files at the given path."""
        if path.is_file():
            return path.suffix in self.extensions
        if path.is_dir():
            return any(
                f.suffix in self.extensions
                for f in path.rglob("*")
                if f.is_file()
            )
        return False

    def parse(self, path: Path) -> Any:
        """
        Parse project files and return a context object.

        The context object is whatever your rules need to operate on.
        For a Python pack, this might include parsed Django models,
        SQLAlchemy table definitions, project structure info, etc.
        """
        raise NotImplementedError(f"Pack '{self.name}' must implement parse()")

    def check(self, path: Path) -> list[Finding]:
        """
        Parse the project and run all registered rules.

        Returns a list of findings sorted by severity.
        """
        context = self.parse(path)
        findings: list[Finding] = []
        for rule in self._rules:
            results = rule.check(context)
            if results:
                findings.extend(results)
        return sorted(findings, key=lambda f: (f.severity.priority, f.code))
