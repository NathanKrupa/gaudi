"""Fixture for SEC-012: tainted path flowing into open() or Path().

The rule uses the same intra-procedural taint model as SEC-006:
function parameters are tainted; simple renames propagate;
startswith/endswith/membership/urlparse-style checks sanitize.
"""

from pathlib import Path


def read_user_file(filename):
    with open(filename) as f:
        return f.read()


def fetch_report(report_id):
    path = report_id
    return open(path).read()


def read_pathlib(user_path):
    return Path(user_path).read_text()


def open_for_write(target):
    with open(target, "w") as f:
        f.write("x")
