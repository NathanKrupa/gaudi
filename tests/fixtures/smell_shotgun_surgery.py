"""Fixture: Shotgun Surgery."""

TAX_RATE = 0.08


def calculate_order_tax(order):
    return order.subtotal * TAX_RATE


def calculate_invoice_tax(invoice):
    return invoice.amount * TAX_RATE


def calculate_refund_tax(refund):
    return refund.amount * TAX_RATE


def format_tax_line(amount):
    tax = amount * TAX_RATE
    return f"Tax: {tax:.2f}"


def apply_tax(price):
    return price * (1 + TAX_RATE)
