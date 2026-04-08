"""Matching test for src/widget.py."""

import pytest

from src.widget import make_widget


def test_make_widget():
    assert make_widget(3)["size"] == 3


_ = pytest
