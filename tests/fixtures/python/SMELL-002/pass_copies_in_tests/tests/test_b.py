"""Test helpers are deliberately local to each test module."""


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


def test_order_amount():
    assert _make_order(3)["amount"] == 3
