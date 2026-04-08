"""Fixture for STAB-010: module-level ThreadPoolExecutor (no bulkhead)."""

from concurrent.futures import ThreadPoolExecutor

EXECUTOR = ThreadPoolExecutor(max_workers=8)


def schedule(work):
    return EXECUTOR.submit(work)
