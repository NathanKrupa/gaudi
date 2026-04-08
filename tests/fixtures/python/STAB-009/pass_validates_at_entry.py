"""Fixture for STAB-009: validation at the public entry point."""


def process_order(order):
    if not isinstance(order.get("items"), list):
        raise TypeError("items must be a list")
    return _compute_total(order["items"])


def _compute_total(items):
    return sum(item["price"] for item in items)
