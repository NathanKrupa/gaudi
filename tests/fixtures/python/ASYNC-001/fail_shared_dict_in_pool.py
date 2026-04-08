"""Fixture for ASYNC-001: module-level dict mutated inside ThreadPoolExecutor callback."""

from concurrent.futures import ThreadPoolExecutor

CACHE = {}


def worker(key, value):
    CACHE[key] = value


def run():
    with ThreadPoolExecutor(max_workers=4) as pool:
        pool.submit(worker, "k", "v")
