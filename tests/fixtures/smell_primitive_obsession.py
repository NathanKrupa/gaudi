"""Fixture: Primitive Obsession."""


def apply_discount(order):
    if order.status == "active":
        return 0.1
    elif order.status == "premium":
        return 0.2
    elif order.status == "vip":
        return 0.3
    return 0


def get_label(order):
    if order.status == "active":
        return "Active Customer"
    elif order.status == "premium":
        return "Premium Customer"
    return "Standard"


def check_flag(value):
    if value == 1:
        return "yes"
    return "no"
