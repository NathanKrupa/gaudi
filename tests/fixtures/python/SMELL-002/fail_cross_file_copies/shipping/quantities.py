"""Shipping quantities."""


def _coerce_parcel_count(raw: object, label: str) -> int:
    """Check a parcel count read from the shipping config."""
    if isinstance(raw, bool):
        raise ValueError(f"{label} must be a positive integer, got boolean")
    if isinstance(raw, int) and raw > 0:
        return raw
    raise ValueError(f"{label} must be a positive integer, got {raw!r}")
