"""Fixture for PY314-004: return/break/continue inside finally swallow exceptions."""


def lookup():
    try:
        return 1
    finally:
        return 2  # noqa: B012


def loop():
    for _ in range(3):
        try:
            pass
        finally:
            break  # noqa: B012
