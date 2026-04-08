"""Fixture for STRUCT-010: sys.path manipulation via .insert and .append."""

import sys

sys.path.insert(0, "/some/other/place")
sys.path.append("/yet/another")
