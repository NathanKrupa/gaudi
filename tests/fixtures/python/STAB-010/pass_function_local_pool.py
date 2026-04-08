"""Fixture for STAB-010: pool scoped to a single function (per-call bulkhead)."""

from concurrent.futures import ThreadPoolExecutor


def fan_out(work, items):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(work, items))
