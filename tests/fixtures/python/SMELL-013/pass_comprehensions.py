"""Fixture for SMELL-013: comprehensions and builtins instead of accumulators."""


def doubled(items):
    return [item * 2 for item in items]


def total(items):
    return sum(items)
