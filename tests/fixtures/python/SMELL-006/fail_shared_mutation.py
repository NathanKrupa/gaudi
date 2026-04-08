"""Fixture for SMELL-006: two functions mutate the same module-level dict."""

CACHE = {}


def store(key, value):
    CACHE[key] = value


def clear(key):
    CACHE.pop(key, None)
