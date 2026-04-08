"""Fixture for SMELL-003: short functions are below the 25-line threshold."""


def add(a, b):
    return a + b


def total(items):
    return sum(item.price for item in items)
