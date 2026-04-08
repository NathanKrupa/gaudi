"""Fixture for SMELL-011: enum comparisons are not string literals."""

from enum import Enum


class Status(Enum):
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"


def handle(order):
    if order.status == Status.PENDING:
        return 0
    if order.status == Status.PAID:
        return 1
    if order.status == Status.SHIPPED:
        return 2
    return -1
