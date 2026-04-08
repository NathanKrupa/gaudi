"""Fixture for SMELL-017: a chain of depth 3 is below the threshold."""


def address(order):
    return order.customer.address
