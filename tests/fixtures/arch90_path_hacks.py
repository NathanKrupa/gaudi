"""Fixture: sys.path hacks."""

import sys

sys.path.insert(0, "/some/path")
sys.path.append("../lib")

import some_module  # noqa: E402
