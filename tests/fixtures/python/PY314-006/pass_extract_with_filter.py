"""Fixture for PY314-006: filter='data' is the safe default."""

import tarfile


def unpack(path, dest):
    with tarfile.open(path) as tf:
        tf.extractall(dest, filter="data")


def unpack_one(path, member, dest):
    with tarfile.open(path) as tf:
        tf.extract(member, dest, filter="data")
