"""Fixture for HTTP-SCALE-001: every requests call declares a timeout."""

import requests


def fetch(url):
    return requests.get(url, timeout=5)


def submit(url, payload):
    return requests.post(url, json=payload, timeout=10)
