"""Fixture for STAB-009: validation in private helper rather than at entry point."""


def process_order(order):
    return _compute_total(order["items"])


def _compute_total(items):
    if not isinstance(items, list):
        raise TypeError("items must be a list")
    return sum(item["price"] for item in items)
