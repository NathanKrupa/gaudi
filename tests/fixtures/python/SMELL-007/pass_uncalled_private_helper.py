"""Fixture for SMELL-007: a private method no other method calls.

``_describe`` touches only an injected dependency, so its attribute set is
empty. Nothing calls it, so it must not become a group of its own merely
for being private (gaudi#281).
"""


class Ledger:
    def __init__(self, clock):
        self.clock = clock
        self.entries = []
        self.total = 0

    def add(self, amount):
        self.entries.append(amount)
        self.total += amount

    def remove_last(self):
        self.total -= self.entries.pop()

    def summary(self):
        return {"count": len(self.entries), "total": self.total}

    def _describe(self):
        return f"ledger at {self.clock.now()}"
