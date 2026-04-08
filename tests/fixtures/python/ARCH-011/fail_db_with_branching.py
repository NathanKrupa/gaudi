"""Fixture for ARCH-011: a function in a db-layer file with if/else business logic."""


def fetch(user_id, mode):
    if mode == "active":
        return {"id": user_id, "active": True}
    else:
        return {"id": user_id, "active": False}
