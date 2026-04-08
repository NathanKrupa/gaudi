"""Fixture for PY314-002: unrelated imports from non-deprecated modules."""

from asyncio import sleep
from locale import setlocale

_ = (sleep, setlocale)
