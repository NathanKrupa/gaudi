"""Fixture for STAB-004: @cache and @lru_cache(maxsize=None) -- both unbounded."""

from functools import cache, lru_cache


@cache
def expensive(x):
    return x * x


@lru_cache(maxsize=None)
def also_expensive(x):
    return x * x
