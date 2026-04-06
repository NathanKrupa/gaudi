"""
Gaudí — Not just structurally sound. Beautiful.

A universal architecture linter for AI-assisted development.
"""

from importlib.metadata import version as _version

__version__ = _version("gaudi-linter")

from gaudi.core import Finding, Rule, Severity, Category
from gaudi.engine import Engine
from gaudi.pack import Pack

__all__ = [
    "Finding",
    "Rule",
    "Severity",
    "Category",
    "Engine",
    "Pack",
]
