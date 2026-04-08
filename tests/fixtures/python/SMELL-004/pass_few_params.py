"""Fixture for SMELL-004: a function with few params is below threshold."""


def build_user(name, email, age):
    return {"name": name, "email": email, "age": age}
