"""Fixture for SEC-004: built-in eval() and exec() in production code."""


def evaluate(expr):
    return eval(expr)


def run(snippet):
    exec(snippet)
