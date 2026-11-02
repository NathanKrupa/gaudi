"""Fixture for SMELL-007: a pipeline of private helpers, each calling the next.

Each step touches only its own slice of state, so attribute sets alone look
disjoint. A private method is a piece of its caller extracted for size, so a
``self._step()`` call joins caller and callee into one group (gaudi#281).
"""


def load_rules(path):
    return {"path": path}


class BatchResolver:
    def __init__(self, provider, *, rules_path, retries=3):
        self.provider = provider
        self._rules = load_rules(rules_path)
        self._attempts = retries
        self._log = []

    def resolve_batch(self, rows):
        return [self._resolve_one(row) for row in rows]

    def _resolve_one(self, row):
        candidate = self._fetch(row)
        return self._finalize(candidate)

    def _fetch(self, row):
        return self.provider.candidates_for(row)

    def _finalize(self, candidate):
        if candidate in self._rules:
            return None
        return self._persist(candidate)

    def _persist(self, candidate):
        for _ in range(self._attempts):
            self._log.append(candidate)
        return candidate
