"""Fixture for STAB-009: private helper without isinstance/raise patterns."""


def public(value):
    return _double(value)


def _double(value):
    return value * 2
