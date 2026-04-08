"""Fixture for SMELL-018: 3 of 3 non-dunder methods are pure delegation."""


class ServiceProxy:
    def __init__(self, service):
        self._service = service

    def fetch(self, key):
        return self._service.fetch(key)

    def store(self, key, value):
        return self._service.store(key, value)

    def delete(self, key):
        return self._service.delete(key)
