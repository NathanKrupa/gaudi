"""Boundary fixture for TEST-STRUCT-002: 2 fixture dependencies is below threshold."""

import pytest


@pytest.fixture
def alpha():
    return 1


@pytest.fixture
def beta():
    return 2


@pytest.fixture
def composed(alpha, beta):
    return alpha + beta
