"""Fixture for SMELL-007: methods all touch overlapping attribute groups."""


class Account:
    def __init__(self):
        self.balance = 0
        self.owner = ""
        self.history = []

    def deposit(self, amount):
        self.balance += amount
        self.history.append(("deposit", amount))

    def withdraw(self, amount):
        self.balance -= amount
        self.history.append(("withdraw", amount))

    def rename(self, new_owner):
        self.owner = new_owner
        self.history.append(("rename", new_owner))
