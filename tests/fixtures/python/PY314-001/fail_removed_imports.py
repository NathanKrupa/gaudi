"""Fixture for PY314-001: importing names removed in Python 3.14."""

from ast import Num
from asyncio import set_child_watcher
from sqlite3 import version

_ = (Num, set_child_watcher, version)
