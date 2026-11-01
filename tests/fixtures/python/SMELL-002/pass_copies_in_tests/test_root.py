"""Test support helpers; each test-path shape on its own."""


def _make_order(amount, cancelled=False):
    order = {"amount": amount, "cancelled": cancelled}
    if cancelled:
        order["status"] = "void"
    return order


def _make_refund(amount, cancelled=False):
    order = {"amount": amount, "cancelled": cancelled}
    if cancelled:
        order["status"] = "void"
    return order
