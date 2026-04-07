"""Fixture for SEC-002: SQL execution built from interpolated strings."""


def lookup_user_fstring(conn, user_id):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchall()


def lookup_user_format(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))
    return cursor.fetchall()


def lookup_user_concat(conn, user_id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = " + str(user_id))
    return cursor.fetchall()


def lookup_user_django_raw(model, user_id):
    return model.objects.raw(f"SELECT * FROM users WHERE id = {user_id}")
