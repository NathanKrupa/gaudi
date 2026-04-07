"""Fixture for TEST-SCALE-001: cheap fixtures (no expensive-resource name) are out of scope."""

import pytest


@pytest.fixture
def sample_data():
    return [1, 2, 3]


@pytest.fixture()
def config():
    return {"debug": True}
