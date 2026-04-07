"""Fixture for SEC-002: a static SQL string with no interpolation is fine."""


def list_users(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM users")
    return cursor.fetchall()
