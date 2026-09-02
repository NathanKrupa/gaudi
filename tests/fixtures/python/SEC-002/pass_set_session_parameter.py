"""Fixture for SEC-002: a SET statement cannot take a bind parameter.

Postgres's SET does not accept placeholders, so `SET statement_timeout = %s`
is a syntax error, not a safer query. Every estate hit on this shape was a
cosmetic hoist of the same f-string into a constant that then had to be
f-string-interpolated anyway.

The parameter NAME must be literal for the exemption to apply -- see
fail_interpolated_set_target.py for the shape that still fires.
"""


def apply_timeout(cursor, milliseconds: int) -> None:
    cursor.execute(f"SET statement_timeout = {milliseconds}")
    cursor.execute("SET lock_timeout = %s" % milliseconds)
    cursor.execute("SET idle_in_transaction_session_timeout TO {}".format(milliseconds))
