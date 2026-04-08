"""Fixture for SMELL-021: 3 unrelated classes with same shape but different method names."""


class FileStore:
    def save(self, item):
        return item

    def load(self, key):
        return key


class CacheStore:
    def put(self, item):
        return item

    def fetch(self, key):
        return key


class DBStore:
    def insert(self, item):
        return item

    def query(self, key):
        return key
