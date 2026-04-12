"""Fixture for STAB-001: filter chains terminated by .first()/.get()/.count()/.exists() are bounded."""


def first_filtered(Order, status):
    return Order.objects.filter(status=status).first()


def get_filtered(Order, pk):
    return Order.objects.filter(pk=pk).get()


def count_filtered(Order, status):
    return Order.objects.filter(status=status).count()


def exists_filtered(Order, status):
    return Order.objects.filter(status=status).exists()


def chained_select_first(Order, status):
    return Order.objects.filter(status=status).select_related("customer").first()
