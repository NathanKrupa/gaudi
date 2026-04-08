"""Fixture for SMELL-017: a chain of depth 5 trips the threshold."""


def address(order):
    return order.customer.account.profile.address.street
