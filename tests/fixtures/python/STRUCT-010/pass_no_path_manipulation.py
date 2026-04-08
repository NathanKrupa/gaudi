"""Fixture for STRUCT-010: a file that uses sys for other things, not path."""

import sys


def write(msg):
    sys.stdout.write(msg)
