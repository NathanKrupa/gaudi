"""Fixture: Public functions missing return type annotations."""


def calculate_total(items):
    return sum(item.price for item in items)


def get_user_name(user):
    return user.first_name + " " + user.last_name


def _private_helper(x):
    return x * 2


def typed_function(x: int) -> int:
    return x + 1
