"""Fixture for PY314-005: comparing with `is NotImplemented` is the canonical safe form."""


def check(result):
    if result is NotImplemented:
        return None
    return result
