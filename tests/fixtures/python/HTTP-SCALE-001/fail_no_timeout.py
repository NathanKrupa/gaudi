"""Fixture for HTTP-SCALE-001: requests calls without a timeout."""

import requests


def fetch(url):
    return requests.get(url)


def submit(url, payload):
    return requests.post(url, json=payload)
