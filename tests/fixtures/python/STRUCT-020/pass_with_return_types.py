"""Fixture for STRUCT-020: public functions declare their return types."""


def total(items: list[int]) -> int:
    return sum(items)


def greeting(name: str) -> str:
    return f"hello {name}"
