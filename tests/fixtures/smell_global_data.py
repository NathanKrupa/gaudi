"""Fixture: Global Data."""

REGISTRY = {}
_CACHE = []
CONFIG = {"debug": True, "version": "1.0"}

MAX_RETRIES = 3
APP_NAME = "myapp"


def register(name, handler):
    REGISTRY[name] = handler


def get_cached():
    return list(_CACHE)
