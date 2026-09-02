"""Fixture for SEC-002: the SET exemption does not cover an interpolated target.

`SET {name} = 5` interpolates the parameter *name*, which is the injection the
rule exists to catch. Only a literal `SET <identifier>` prefix is exempt.
"""


def apply(cursor, name: str) -> None:
    cursor.execute(f"SET {name} = 5")
