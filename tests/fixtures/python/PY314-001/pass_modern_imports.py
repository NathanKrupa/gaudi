"""Fixture for PY314-001: replacements for the removed APIs."""

from ast import Constant
from importlib.util import find_spec
from sqlite3 import sqlite_version

_ = (Constant, find_spec, sqlite_version)
