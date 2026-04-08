"""Fixture for STRUCT-021: the literal "approved" appears 3 times."""


def lookup_a(record):
    if record["status"] == "approved":
        return True
    return False


def lookup_b(record):
    return record["status"] == "approved"


def label(record):
    return "approved" if record["ok"] else "pending"
