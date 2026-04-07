"""Fixture for ERR-003: a handler that doesn't log is out of scope (ERR-001's job)."""


def process(item):
    try:
        return item.do_work()
    except RuntimeError:
        return None
