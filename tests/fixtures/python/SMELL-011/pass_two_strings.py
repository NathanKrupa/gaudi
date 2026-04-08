"""Fixture for SMELL-011: 2 string comparisons is below the >= 3 threshold."""


def handle(order):
    if order.status == "pending":
        return 0
    if order.status == "paid":
        return 1
    return -1
