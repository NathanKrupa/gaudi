"""Fixture for PY314-004: a try/except with no finally block at all."""


def lookup():
    try:
        return 1
    except ValueError:
        return 0
