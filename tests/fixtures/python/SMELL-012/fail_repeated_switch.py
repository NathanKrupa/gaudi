"""Fixture for SMELL-012: same status switch in 2 functions."""


def label(status):
    if status == "pending":
        return "Pending"
    elif status == "paid":
        return "Paid"
    elif status == "shipped":
        return "Shipped"
    return "?"


def color(status):
    if status == "pending":
        return "yellow"
    elif status == "paid":
        return "green"
    elif status == "shipped":
        return "blue"
    return "gray"
