"""Fixture for STAB-001: .filter() and .select_related() are query-building, not materializing."""


class Manager:
    objects = None


def get_filtered():
    return Manager.objects.filter(active=True).select_related("profile")


def get_excluded():
    return Manager.objects.exclude(deleted=True).prefetch_related("items")
