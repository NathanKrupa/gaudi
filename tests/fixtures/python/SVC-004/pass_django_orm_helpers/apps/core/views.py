"""Fixture for SVC-004: django.db.models is framework, not another app's models.

`Count` and `Q` are ORM primitives re-exported from django.db.models. The rule
was reading the module's `db` segment as an app name and every importing app as
a coupled consumer of it (#214).
"""

from django.db.models import Count, Q


def summarise(queryset):
    return queryset.filter(Q(active=True)).aggregate(total=Count("id"))
