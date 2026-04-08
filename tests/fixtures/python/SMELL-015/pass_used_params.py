"""Fixture for SMELL-015: parameters are actually used."""


def fetch(url, headers=None, timeout=None):
    if headers is None:
        headers = {}
    if timeout is None:
        timeout = 30
    return (url, headers, timeout)
