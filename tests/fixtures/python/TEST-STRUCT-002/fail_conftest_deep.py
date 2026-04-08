"""Fixture for TEST-STRUCT-002: a fixture depending on 4 other fixtures."""

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
def delta():
    return 4


@pytest.fixture
def composed(alpha, beta, gamma, delta):
    return alpha + beta + gamma + delta
