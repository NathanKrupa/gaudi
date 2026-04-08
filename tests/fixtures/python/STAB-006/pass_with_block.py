"""Fixture for STAB-006: open() inside a `with` block manages cleanup."""


def read_text(path):
    with open(path) as f:
        return f.read()
