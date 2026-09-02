"""Second app importing the same django.db.models helpers -- still not coupling."""

from django.db.models import Count, Q


def summarise(queryset):
    return queryset.filter(Q(paid=True)).aggregate(total=Count("id"))
