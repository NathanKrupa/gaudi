"""Fixture: Insider Trading."""


class Account:
    def __init__(self):
        self.balance = 0
        self.transactions = []


class TransferService:
    def transfer(self, source, dest, amount):
        source.balance -= amount
        dest.balance += amount
        source.transactions.append(f"sent {amount}")
        dest.transactions.append(f"received {amount}")


class AuditService:
    def audit(self, account):
        return len(account.transactions)
