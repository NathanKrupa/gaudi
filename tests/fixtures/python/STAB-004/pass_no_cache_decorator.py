"""Fixture for STAB-004: a function with no caching decorator at all."""


def expensive(x):
    return x * x
