"""Fixture for ARCH-020: a module-level factory function reading os.getenv is fine."""

import os


def make_client():
    api_key = os.getenv("API_KEY")
    return {"api_key": api_key}
