"""Fixture for SEC-010: tempfile.mktemp is race-condition prone."""

import tempfile
from tempfile import mktemp


def write_report(data: str) -> str:
    path = tempfile.mktemp(suffix=".txt")
    with open(path, "w") as f:
        f.write(data)
    return path


def another_temp(data: str) -> str:
    path = mktemp()
    with open(path, "w") as f:
        f.write(data)
    return path
