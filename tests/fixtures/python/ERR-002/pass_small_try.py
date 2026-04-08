"""Fixture for ERR-002: a focused try block wrapping a single risky call."""


def parse(text):
    try:
        return int(text)
    except ValueError:
        return None
