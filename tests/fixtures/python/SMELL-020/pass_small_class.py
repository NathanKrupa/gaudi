"""Fixture for SMELL-020: small focused class is below thresholds."""


class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        self.value += 1

    def reset(self):
        self.value = 0
