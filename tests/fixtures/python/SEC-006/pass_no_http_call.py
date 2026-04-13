"""Fixture for SEC-006: functions that don't make HTTP calls."""


def process_url(url):
    return url.strip().lower()


def build_url(base, path):
    return f"{base}/{path}"
