"""Fixture for SMELL-007: a public method fronting two unrelated groups.

``save_all`` calls public methods of both groups. A public method is its own
entry point, not an extracted piece of its caller, so the call does not join
the groups: the class still changes for two reasons.
"""


class ProfileAndInvoice:
    def __init__(self):
        self.name = ""
        self.email = ""
        self.invoice_lines = []
        self.invoice_total = 0

    def rename(self, name):
        self.name = name
        self.email = self.email or f"{name}@example.org"

    def add_line(self, amount):
        self.invoice_lines.append(amount)
        self.invoice_total += amount

    def save_all(self, name, amount):
        self.rename(name)
        self.add_line(amount)
