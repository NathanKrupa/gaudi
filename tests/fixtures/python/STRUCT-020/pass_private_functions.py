"""Fixture for STRUCT-020: leading-underscore functions are private and exempt."""


def _total(items):
    return sum(items)


def _greeting(name):
    return f"hello {name}"
