"""
Gaudí — Not just structurally sound. Beautiful.

A universal architecture linter for AI-assisted development.
"""

__version__ = "0.1.0"

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
