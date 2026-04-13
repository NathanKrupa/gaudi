"""Fixture for SEC-006: sanitized URLs should not trigger."""

import requests
from urllib.parse import urlparse


ALLOWED_HOSTS = {"api.example.com", "internal.example.com"}


def fetch_after_urlparse(user_url):
    parsed = urlparse(user_url)
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Host not allowed")
    return requests.get(user_url)


def fetch_after_startswith(url):
    if not url.startswith("https://api.example.com"):
        raise ValueError("Bad URL")
    return requests.get(url)


def fetch_after_in_check(url):
    if url not in ALLOWED_HOSTS:
        raise ValueError("Not allowed")
    return requests.get(url)
