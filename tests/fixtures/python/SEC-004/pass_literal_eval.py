"""Fixture for SEC-004: ast.literal_eval is the safe parser for trusted-shape literals."""

import ast


def evaluate(expr):
    return ast.literal_eval(expr)
