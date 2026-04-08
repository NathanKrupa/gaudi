"""Fixture for STAB-001: ORM .all()/.filter() chained from .objects with no limit."""


def list_orders(Order):
    return Order.objects.all()


def find_orders(Order, status):
    return Order.objects.filter(status=status)
