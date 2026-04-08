"""Fixture for STRUCT-021: 2 uses is below the >= 3 threshold."""


def lookup_a(record):
    return record["status"] == "approved"


def lookup_b(record):
    return record["status"] == "approved"
