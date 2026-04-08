"""Fixture for STAB-007: a positional first argument is also a valid bound."""

from concurrent.futures import ThreadPoolExecutor


def parallel(work, items):
    with ThreadPoolExecutor(8) as pool:
        return list(pool.map(work, items))
