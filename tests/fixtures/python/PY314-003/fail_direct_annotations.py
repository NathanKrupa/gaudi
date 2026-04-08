"""Fixture for PY314-003: direct __annotations__ access (deferred-evaluation hazard)."""


def get_hints(cls):
    return cls.__annotations__


def find_field(obj, name):
    return obj.__annotations__.get(name)
