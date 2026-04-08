"""Fixture for PY314-006: a file that never mentions the tar module is short-circuited."""

import zipfile


def unpack(path, dest):
    with zipfile.ZipFile(path) as zf:
        zf.extractall(dest)
