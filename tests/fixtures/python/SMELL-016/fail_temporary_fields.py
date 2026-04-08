"""Fixture for SMELL-016: 2 attributes only set in one non-init method."""


class Calculator:
    def __init__(self):
        self.result = 0

    def trace(self, items):
        self.trace_log = []
        self.trace_count = 0
        for item in items:
            self.trace_log.append(item)
            self.trace_count += 1
