"""Fixture for PY314-005: returning NotImplemented from __eq__ is fine -- it's only a hazard in bool context."""


class Vec:
    def __init__(self, x):
        self.x = x

    def __eq__(self, other):
        if not isinstance(other, Vec):
            return NotImplemented
        return self.x == other.x
