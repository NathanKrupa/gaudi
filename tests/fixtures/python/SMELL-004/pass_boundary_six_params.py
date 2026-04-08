"""Fixture for SMELL-004: exactly 6 params is at the boundary (> 6 is the trigger)."""


def build_user(name, email, age, address, phone, role):
    return (name, email, age, address, phone, role)
