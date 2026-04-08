"""Fixture for PY314-003: typing.get_type_hints respects deferred annotations."""

import typing


def get_hints(cls):
    return typing.get_type_hints(cls)
