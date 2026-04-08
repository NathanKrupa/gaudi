"""Fixture for STAB-007: ThreadPoolExecutor with explicit max_workers."""

from concurrent.futures import ThreadPoolExecutor


def parallel(work, items):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(work, items))
