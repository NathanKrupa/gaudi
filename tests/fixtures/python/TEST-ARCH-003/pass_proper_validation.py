"""Fixture for TEST-ARCH-003: validation via raised exceptions, not assert."""


def transfer_funds(source, dest, amount):
    if amount <= 0:
        raise ValueError("amount must be positive")
    source.balance -= amount
    dest.balance += amount
    return dest.balance
