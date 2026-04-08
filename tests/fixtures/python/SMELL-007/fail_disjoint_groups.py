"""Fixture for SMELL-007: methods touch two disjoint attribute groups."""


class UserAndReport:
    def __init__(self):
        self.name = ""
        self.email = ""
        self.report_title = ""
        self.report_rows = []

    def set_name(self, name):
        self.name = name

    def set_email(self, email):
        self.email = email

    def set_title(self, title):
        self.report_title = title

    def add_row(self, row):
        self.report_rows.append(row)
