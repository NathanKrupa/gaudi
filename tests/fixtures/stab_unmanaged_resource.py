# Fixture for STAB-006: UnmanagedResource
# ruff: noqa: F821


# BAD: bare open() - file handle leaks on exception
def read_config():
    f = open("config.txt")
    data = f.read()
    f.close()
    return data


# BAD: another bare open
def write_log(msg):
    f = open("log.txt", "a")
    f.write(msg)
    f.close()


# BAD: bare Session() - connection pool exhaustion
def get_user(user_id):
    session = Session()
    return session.query(User).get(user_id)


# GOOD: context manager handles cleanup
def safe_read():
    with open("config.txt") as f:
        return f.read()


# GOOD: Session with context manager
def safe_get_user(user_id):
    with Session() as session:
        return session.query(User).get(user_id)


# GOOD: Session with yield (dependency injection)
def get_session():
    session = Session()
    yield session
    session.close()
