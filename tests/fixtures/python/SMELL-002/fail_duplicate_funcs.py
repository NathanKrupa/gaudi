"""Fixture for SMELL-002: two functions with identical normalized structure."""


def total_orders(orders):
    total = 0
    for order in orders:
        total += order.amount
    return total


def total_invoices(invoices):
    total = 0
    for invoice in invoices:
        total += invoice.amount
    return total
