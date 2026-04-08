"""Fixture for PY314-002: replacements for the deprecated APIs."""

from inspect import iscoroutinefunction
from locale import getlocale

_ = (iscoroutinefunction, getlocale)
