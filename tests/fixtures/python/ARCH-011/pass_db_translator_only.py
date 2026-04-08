"""Fixture for ARCH-011: a db-layer file that only translates -- no if/else branching."""


def fetch(user_id):
    return {"id": user_id}


def store(record):
    return record
