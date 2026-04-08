"""Boundary fixture for TEST-ARCH-001: 4 @patch decorators is below threshold."""

from unittest.mock import patch

import pytest


@patch("module.dep_one")
@patch("module.dep_two")
@patch("module.dep_three")
@patch("module.dep_four")
def test_four_patches(_one, _two, _three, _four):
    assert True


_ = pytest
