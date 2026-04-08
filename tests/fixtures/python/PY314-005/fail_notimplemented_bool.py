"""Fixture for PY314-005: NotImplemented in a boolean context (now TypeError in 3.14)."""


def check(x):
    if NotImplemented:  # noqa: B015
        return x
    return None


def loop():
    while NotImplemented:  # noqa: B015
        break
