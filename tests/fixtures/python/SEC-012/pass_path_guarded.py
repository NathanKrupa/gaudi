"""Passing fixture for SEC-012: sanitized or constant paths."""

from pathlib import Path

ALLOWED_REPORTS = {"alpha", "beta", "gamma"}


def read_allowed(user_path):
    if user_path in ALLOWED_REPORTS:
        return open(user_path).read()
    return ""


def read_prefixed(user_path):
    if user_path.startswith("/var/reports/"):
        return open(user_path).read()
    return ""


def read_suffixed(user_path):
    if user_path.endswith(".txt"):
        return Path(user_path).read_text()
    return ""


def read_constant():
    return open("/etc/config.ini").read()


def read_local_constant():
    path = "/etc/hosts"
    return open(path).read()
