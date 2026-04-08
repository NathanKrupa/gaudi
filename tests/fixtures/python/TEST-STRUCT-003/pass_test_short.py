"""Fixture for TEST-STRUCT-003: a concise three-line test."""

import pytest


def test_short():
    result = 1 + 1
    assert result == 2
