"""Fixture for ERR-004: a named exception handler whose body is just `pass`."""


def fetch(client, key):
    try:
        return client.get(key)
    except ValueError:
        pass
