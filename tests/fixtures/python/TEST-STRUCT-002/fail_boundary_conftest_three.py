"""Boundary fixture for TEST-STRUCT-002: exactly 3 fixture dependencies trips the rule."""

import pytest


@pytest.fixture
def alpha():
    return 1


@pytest.fixture
def beta():
    return 2


@pytest.fixture
def gamma():
    return 3


@pytest.fixture
def composed(alpha, beta, gamma):
    return alpha + beta + gamma
