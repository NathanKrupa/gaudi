"""Fixture for SMELL-011: order.status compared to 4 string literals."""


def handle(order):
    if order.status == "pending":
        return 0
    if order.status == "paid":
        return 1
    if order.status == "shipped":
        return 2
    if order.status == "delivered":
        return 3
    return -1
