"""Fixture for HTTP-SCALE-001: a `.get()` call on a non-requests object is out of scope."""

import requests


def lookup(mapping, key):
    return mapping.get(key)


_ = requests
