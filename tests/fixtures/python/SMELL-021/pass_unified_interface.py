"""Fixture for SMELL-021: classes share a unified interface (Protocol)."""

from typing import Protocol


class Store(Protocol):
    def save(self, item): ...
    def load(self, key): ...


class FileStore:
    def save(self, item):
        return item

    def load(self, key):
        return key


class CacheStore:
    def save(self, item):
        return item

    def load(self, key):
        return key


class DBStore:
    def save(self, item):
        return item

    def load(self, key):
        return key
