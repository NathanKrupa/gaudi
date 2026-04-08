"""Fixture for STAB-001: methods not in the unbounded set are out of scope."""


def first_order(Order):
    return Order.objects.first()


def get_one(Order, pk):
    return Order.objects.get(pk=pk)
