"""Fixture for SMELL-013: accumulation loops replaceable by comprehensions."""


def doubled(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result


def total(items):
    sum_ = 0
    for item in items:
        sum_ += item
    return sum_
