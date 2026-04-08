"""Fixture for STRUCT-021: the literal is extracted to a named constant."""

STATUS_APPROVED = "approved"


def lookup_a(record):
    if record["status"] == STATUS_APPROVED:
        return True
    return False


def lookup_b(record):
    return record["status"] == STATUS_APPROVED
