"""Fixture for ERR-001: each handler names the exception it expects."""


def parse(text):
    try:
        return int(text)
    except ValueError:
        return None


def load(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""
