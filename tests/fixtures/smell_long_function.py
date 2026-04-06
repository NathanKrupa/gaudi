"""Fixture: Long Function."""


def process_order(order):
    customer = order["customer"]
    items = order["items"]
    subtotal = 0
    for item in items:
        price = item["price"]
        qty = item["quantity"]
        line_total = price * qty
        subtotal += line_total
    tax_rate = 0.08
    tax = subtotal * tax_rate
    total = subtotal + tax
    discount = 0
    if total > 100:
        discount = total * 0.1
    total -= discount
    shipping = 5.99
    if total > 50:
        shipping = 0
    total += shipping
    payment = order.get("payment_method", "card")
    if payment == "card":
        fee = total * 0.03
        total += fee
    invoice = {
        "customer": customer,
        "subtotal": subtotal,
        "tax": tax,
        "discount": discount,
        "shipping": shipping,
        "total": total,
    }
    return invoice


def short_fn():
    return 42
