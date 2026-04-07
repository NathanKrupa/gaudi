"""Fixture for TEST-SCALE-001: expensive fixtures declare a wider scope."""

import pytest


@pytest.fixture(scope="session")
def database():
    return {"connected": True}


@pytest.fixture(scope="module")
def client():
    return object()
