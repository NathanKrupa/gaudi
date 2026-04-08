"""Fixture for ARCH-011: branching is fine in non-data-layer files."""


def process(payload, mode):
    if mode == "draft":
        return {"saved": False, **payload}
    else:
        return {"saved": True, **payload}
