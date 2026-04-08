"""Fixture for SMELL-005: empty mutable containers at module scope."""

REGISTRY = {}
_CACHE = []


def register(name, handler):
    REGISTRY[name] = handler


def cached():
    return list(_CACHE)
