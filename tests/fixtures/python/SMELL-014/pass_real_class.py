"""Fixture for SMELL-014: class with multiple methods is not lazy."""


class Calculator:
    def __init__(self):
        self.value = 0

    def add(self, n):
        self.value += n

    def reset(self):
        self.value = 0
