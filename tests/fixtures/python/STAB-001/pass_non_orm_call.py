"""Fixture for STAB-001: a `.all()` call on a non-ORM object is out of scope."""


def all_truthy(items):
    return all(items)


def get_first(mapping, key):
    return mapping.filter
