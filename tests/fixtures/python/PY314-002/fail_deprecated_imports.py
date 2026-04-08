"""Fixture for PY314-002: imports deprecated in Python 3.14."""

import pty
from asyncio import iscoroutinefunction
from locale import getdefaultlocale

_ = (pty, iscoroutinefunction, getdefaultlocale)
