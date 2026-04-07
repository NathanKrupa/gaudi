# Negative fixture for CPLX-001: deep module -- few public names, rich implementation


def process_order(order):
    """A deep public entry point with substantial implementation behind it."""
    validated = _validate(order)
    priced = _price(validated)
    confirmed = _confirm(priced)
    _persist(confirmed)
    _notify(confirmed)
    return confirmed


def _validate(order):
    if not order.items:
        raise ValueError("empty order")
    for item in order.items:
        if item.qty <= 0:
            raise ValueError("bad qty")
        if item.price < 0:
            raise ValueError("bad price")
    return order


def _price(order):
    subtotal = sum(i.qty * i.price for i in order.items)
    tax = subtotal * 0.08
    order.total = subtotal + tax
    return order


def _confirm(order):
    order.status = "confirmed"
    order.confirmation_code = order.id * 7
    return order


def _persist(order):
    with open("/tmp/orders.log", "a") as f:
        f.write(f"{order.id}:{order.total}\n")


def _notify(order):
    print(f"Order {order.id} confirmed: ${order.total}")
