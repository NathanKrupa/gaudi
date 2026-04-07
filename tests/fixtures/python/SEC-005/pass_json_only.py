"""Fixture for SEC-005: json.load is not in scope."""

import json


def load_blob(path):
    with open(path) as f:
        return json.load(f)
