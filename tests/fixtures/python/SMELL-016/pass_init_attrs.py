"""Fixture for SMELL-016: all attributes initialized in __init__."""


class Calculator:
    def __init__(self):
        self.result = 0
        self.trace_log = []
        self.trace_count = 0

    def trace(self, items):
        self.trace_log = []
        self.trace_count = 0
        for item in items:
            self.trace_log.append(item)
            self.trace_count += 1
