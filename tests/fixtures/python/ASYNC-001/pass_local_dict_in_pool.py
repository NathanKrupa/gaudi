"""Fixture for ASYNC-001: dict is local, not module-level shared state."""

from concurrent.futures import ThreadPoolExecutor


def worker(key, value):
    local_cache = {}
    local_cache[key] = value
    return local_cache


def run():
    with ThreadPoolExecutor(max_workers=4) as pool:
        pool.submit(worker, "k", "v")
