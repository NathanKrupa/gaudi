"""Fixture for TEST-ARCH-001: a single mock is well below threshold."""

from unittest.mock import patch

import pytest


@patch("module.dep_one")
def test_one_mock(_one):
    assert True


_ = pytest
