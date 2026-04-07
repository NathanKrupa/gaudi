"""Fixture for LOG-001: an f-string in a non-logger call must not trigger the rule."""


def greet(name):
    return f"hello {name}"


def shout(name):
    print(f"HELLO {name}")
