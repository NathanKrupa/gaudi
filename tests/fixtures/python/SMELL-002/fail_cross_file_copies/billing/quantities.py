"""Billing quantities."""


def _coerce_quantity(value, field):
    """Validate a configured quantity for the billing run."""
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a positive integer, got boolean")
    if isinstance(value, int) and value > 0:
        return value
    raise ValueError(f"{field} must be a positive integer, got {value!r}")
