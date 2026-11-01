"""Fixture for SMELL-002: two functions in one file with identical structure."""


def total_orders(orders):
    total = 0
    for order in orders:
        if order.cancelled:
            continue
        total += order.amount
    return total


def total_invoices(invoices):
    total = 0
    for invoice in invoices:
        if invoice.cancelled:
            continue
        total += invoice.amount
    return total
