"""Fixture for TEST-ARCH-003: assert used as runtime validation in production code."""


def transfer_funds(source, dest, amount):
    assert amount > 0
    source.balance -= amount
    dest.balance += amount
    return dest.balance
