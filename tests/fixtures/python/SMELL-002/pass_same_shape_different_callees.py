"""Fixture for SMELL-002: the same shape calling different collaborators is not a copy."""

from ledger import load_invoices, load_orders


def order_lines(customer, limit):
    rows = load_orders(customer.account_id, limit=limit)
    if not rows:
        return []
    return [row.line for row in rows if row.visible]


def invoice_lines(customer, limit):
    rows = load_invoices(customer.account_id, limit=limit)
    if not rows:
        return []
    return [row.line for row in rows if row.visible]
