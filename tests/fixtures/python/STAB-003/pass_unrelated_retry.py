"""Fixture for STAB-003: an unrelated `retry` symbol with no resilience kwargs is out of scope."""


def retry(work):
    return work()


def run(work):
    return retry(work)
