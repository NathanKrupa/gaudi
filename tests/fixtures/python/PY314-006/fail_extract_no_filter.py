"""Fixture for PY314-006: tarfile.extract/extractall called without an explicit filter."""

import tarfile


def unpack(path, dest):
    with tarfile.open(path) as tf:
        tf.extractall(dest)


def unpack_one(path, member, dest):
    with tarfile.open(path) as tf:
        tf.extract(member, dest)
