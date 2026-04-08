"""Fixture for SMELL-024: clean code without comment overload."""


def total(items):
    return sum(items)


def average(items):
    if not items:
        return 0
    return sum(items) / len(items)
