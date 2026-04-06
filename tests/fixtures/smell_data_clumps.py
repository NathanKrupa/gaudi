"""Fixture: Data Clumps."""


def create_address(street, city, state, zip_code):
    return f"{street}, {city}, {state} {zip_code}"


def validate_address(street, city, state, zip_code):
    return all([street, city, state, zip_code])


def format_address(street, city, state, zip_code, country="US"):
    return f"{street}\n{city}, {state} {zip_code}\n{country}"


def unrelated(name, age):
    return f"{name}: {age}"
