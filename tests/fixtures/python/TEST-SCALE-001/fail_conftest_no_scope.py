"""Fixture for TEST-SCALE-001: expensive fixtures in conftest with no scope= kwarg."""

import pytest


@pytest.fixture
def database():
    return {"connected": True}


@pytest.fixture()
def client():
    return object()
