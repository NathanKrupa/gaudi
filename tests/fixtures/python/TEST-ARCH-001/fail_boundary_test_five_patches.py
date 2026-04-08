"""Boundary fixture for TEST-ARCH-001: exactly 5 @patch decorators trips the rule."""

from unittest.mock import patch

import pytest


@patch("module.dep_one")
@patch("module.dep_two")
@patch("module.dep_three")
@patch("module.dep_four")
@patch("module.dep_five")
def test_five_patches(_one, _two, _three, _four, _five):
    assert True


_ = pytest
