"""Fixture for SMELL-010: street/city/zip appear together in 3 functions."""


def create_address(street, city, zip, country):
    return (street, city, zip, country)


def update_address(user_id, street, city, zip):
    return (user_id, street, city, zip)


def validate_address(street, city, zip):
    return bool(street and city and zip)
