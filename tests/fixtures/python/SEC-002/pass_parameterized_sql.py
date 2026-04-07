"""Fixture for SEC-002: parameterized SQL passes the value as a separate argument."""


def lookup_user(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchall()
