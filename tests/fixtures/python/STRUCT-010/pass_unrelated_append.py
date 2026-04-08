"""Fixture for STRUCT-010: an unrelated `.append` on a list, not on sys.path."""


def collect(items):
    out = []
    for item in items:
        out.append(item)
    return out
