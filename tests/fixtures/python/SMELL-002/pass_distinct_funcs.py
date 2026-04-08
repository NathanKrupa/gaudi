"""Fixture for SMELL-002: functions with distinct structure."""


def total_orders(orders):
    return sum(order.amount for order in orders)


def average_invoice(invoices):
    if not invoices:
        return 0
    return sum(i.amount for i in invoices) / len(invoices)
