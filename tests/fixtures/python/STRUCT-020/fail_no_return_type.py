"""Fixture for STRUCT-020: public top-level functions returning a value but no return type."""


def total(items):
    return sum(items)


def greeting(name):
    return f"hello {name}"
