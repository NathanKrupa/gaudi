"""Passing fixture for SEC-010: mkstemp and NamedTemporaryFile."""

import os
import tempfile


def write_report(data: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(data)
    return path


def write_report_named(data: str) -> str:
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt") as f:
        f.write(data)
        return f.name
