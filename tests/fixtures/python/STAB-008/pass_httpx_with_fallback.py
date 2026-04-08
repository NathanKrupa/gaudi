"""Fixture for STAB-008: httpx call inside try/except."""

import httpx


def post_event(payload):
    try:
        response = httpx.post("https://api.example.com/events", json=payload)
        return response.status_code
    except httpx.HTTPError:
        return None
