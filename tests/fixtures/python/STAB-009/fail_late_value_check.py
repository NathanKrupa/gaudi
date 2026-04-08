"""Fixture for STAB-009: numeric validation deep in helper."""


def withdraw(account, amount):
    return _apply_withdrawal(account, amount)


def _apply_withdrawal(account, amount):
    if not isinstance(amount, (int, float)):
        raise ValueError("amount must be numeric")
    account.balance -= amount
    return account
