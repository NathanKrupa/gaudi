"""Fixture for ERR-006: ValueError on bad arguments is the conventional, allowed case."""


class Range:
    def __init__(self, lo, hi):
        if lo > hi:
            raise ValueError("lo must be <= hi")
        self.lo = lo
        self.hi = hi
