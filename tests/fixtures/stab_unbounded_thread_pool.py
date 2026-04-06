# Fixture for STAB-007: UnboundedThreadPool
from concurrent.futures import ThreadPoolExecutor


# BAD: no max_workers
def run_tasks(tasks):
    with ThreadPoolExecutor() as pool:
        return list(pool.map(lambda t: t(), tasks))


# GOOD: explicit max_workers
def run_bounded(tasks):
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(lambda t: t(), tasks))


# GOOD: positional arg
def run_positional(tasks):
    with ThreadPoolExecutor(8) as pool:
        return list(pool.map(lambda t: t(), tasks))
