"""Fixture for STAB-004: lru_cache with an explicit positive maxsize."""

from functools import lru_cache


@lru_cache(maxsize=128)
def expensive(x):
    return x * x
