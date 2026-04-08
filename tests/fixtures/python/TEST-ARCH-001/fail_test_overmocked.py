"""Fixture for TEST-ARCH-001: a test smothered in @patch decorators."""

from unittest.mock import patch

import pytest


@patch("module.dep_one")
@patch("module.dep_two")
@patch("module.dep_three")
@patch("module.dep_four")
@patch("module.dep_five")
@patch("module.dep_six")
def test_overmocked(_one, _two, _three, _four, _five, _six):
    assert True


_ = pytest
