"""Fixture for STAB-008: httpx call with no try/except fallback."""

import httpx


def post_event(payload):
    response = httpx.post("https://api.example.com/events", json=payload)
    return response.status_code
