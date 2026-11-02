"""Fixture for SMELL-007: a ``__dunder__`` hook called from the other group.

``__len__`` belongs to the invoice group; ``describe`` in the profile group
calls it. A dunder is a protocol hook, not an extracted helper, so the call
does not join the groups and the class is still flagged (gaudi#281).
"""


class ProfileWithInvoice:
    def __init__(self):
        self.name = ""
        self.email = ""
        self.invoice_lines = []
        self.invoice_total = 0

    def rename(self, name):
        self.name = name
        self.email = self.email or f"{name}@example.org"

    def describe(self):
        return f"{self.name} <{self.email}>: {self.__len__()} lines"

    def add_line(self, amount):
        self.invoice_lines.append(amount)
        self.invoice_total += amount

    def __len__(self):
        return len(self.invoice_lines) if self.invoice_total else 0
