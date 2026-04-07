"""Fixture for TEST-STRUCT-001: simple (non-complex) assertions don't require a message."""

import pytest


def test_equality():
    assert 1 + 1 == 2


def test_membership():
    assert "a" in "abc"


def test_truthy():
    assert [1]


_ = pytest
