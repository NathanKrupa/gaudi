"""Fixture for SMELL-018: methods do their own work, not delegation."""


class CacheLayer:
    def __init__(self, store):
        self._store = store
        self._hits = 0

    def fetch(self, key):
        self._hits += 1
        cached = self._store.get(key)
        if cached is None:
            return None
        return cached.value

    def reset(self):
        self._hits = 0

    def stats(self):
        return {"hits": self._hits}
