"""Fixture for ERR-005: only two distinct exception types raised — under threshold."""


def a():
    raise ValueError("a")


def b():
    raise TypeError("b")
