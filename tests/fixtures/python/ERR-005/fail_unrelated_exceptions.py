"""Fixture for ERR-005: module raises four unrelated builtin exceptions."""


def a():
    raise IOError("disk")


def b():
    raise RuntimeError("oops")


def c():
    raise KeyError("missing")


def d():
    raise AttributeError("nope")
