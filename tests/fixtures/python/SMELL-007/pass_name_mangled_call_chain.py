"""Fixture for SMELL-007: a pipeline of name-mangled ``__helper`` methods.

A ``__name`` method is as private as a ``_name`` one, so a ``self.__step()``
call joins caller and callee exactly as ``self._step()`` does (gaudi#281).
"""


def load_rules(path):
    return {"path": path}


class MangledResolver:
    def __init__(self, provider, *, rules_path, retries=3):
        self.provider = provider
        self._rules = load_rules(rules_path)
        self._attempts = retries
        self._log = []

    def resolve_batch(self, rows):
        return [self.__resolve_one(row) for row in rows]

    def __resolve_one(self, row):
        candidate = self.__fetch(row)
        return self.__finalize(candidate)

    def __fetch(self, row):
        return self.provider.candidates_for(row)

    def __finalize(self, candidate):
        if candidate in self._rules:
            return None
        return self.__persist(candidate)

    def __persist(self, candidate):
        for _ in range(self._attempts):
            self._log.append(candidate)
        return candidate
