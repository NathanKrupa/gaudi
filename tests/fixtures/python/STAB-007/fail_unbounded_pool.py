"""Fixture for STAB-007: ThreadPoolExecutor() with no max_workers."""

from concurrent.futures import ThreadPoolExecutor


def parallel(work, items):
    with ThreadPoolExecutor() as pool:
        return list(pool.map(work, items))
