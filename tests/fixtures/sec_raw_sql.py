# Fixture for SEC-002 RawSQLInjection.


def get_user_fstring(conn, user_id):
    # POSITIVE: f-string in execute call
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
    return cursor.fetchall()


def get_user_format(conn, user_id):
    # POSITIVE: .format() in execute call
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))
    return cursor.fetchall()


def get_user_concat(conn, user_id):
    # POSITIVE: string concatenation in execute call
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = " + str(user_id))
    return cursor.fetchall()


def get_user_django_raw(model, user_id):
    # POSITIVE: f-string in .raw() call
    return model.objects.raw(f"SELECT * FROM users WHERE id = {user_id}")


def get_user_safe(conn, user_id):
    # NEGATIVE: parameterized query — should not trigger
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    return cursor.fetchall()


def get_user_constant(conn):
    # NEGATIVE: plain string literal — should not trigger
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users LIMIT 10")
    return cursor.fetchall()
