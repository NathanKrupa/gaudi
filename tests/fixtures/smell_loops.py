"""Fixture: Loops replaceable with pipelines."""


def get_active_names(users):
    result = []
    for user in users:
        if user["active"]:
            result.append(user["name"])
    return result


def sum_prices(items):
    total = 0
    for item in items:
        total += item.price
    return total


def transform(data):
    for item in data:
        item.validate()
        item.process()
        item.save()
