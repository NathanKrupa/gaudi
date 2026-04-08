"""Fixture for SMELL-006: each function uses its own local state."""


def store(key, value):
    cache = {key: value}
    return cache


def clear(d, key):
    new_dict = dict(d)
    new_dict.pop(key, None)
    return new_dict
