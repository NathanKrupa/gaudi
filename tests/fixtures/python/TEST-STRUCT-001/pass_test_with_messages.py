"""Fixture for TEST-STRUCT-001: complex assertions all carry a failure message."""

import pytest


def test_chain_compare():
    x = 5
    assert 0 < x < 10, "x must be in (0, 10)"


def test_bool_op():
    a, b = 1, 2
    assert a > 0 and b > 0, "both inputs must be positive"


def test_negation():
    items = [1, 2, 3]
    assert not (len(items) == 0), "items must not be empty"


_ = pytest
