"""Fixture for PY314-001: imports of unrelated names from the same modules are fine."""

from ast import parse, walk
from sqlite3 import connect

_ = (parse, walk, connect)
