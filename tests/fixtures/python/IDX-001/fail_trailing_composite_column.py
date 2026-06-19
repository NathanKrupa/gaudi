"""Fixture for IDX-001: a trailing composite-index column is not covered.

``code`` is the SECOND column of ``(tenant, code)``. A B-tree composite index
serves prefix lookups on its leading column, not standalone lookups on a
trailing column, so ``code`` still needs its own index — IDX-001 must fire.
"""

from django.db import models


class Product(models.Model):
    tenant = models.IntegerField()
    code = models.CharField(max_length=64)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "code"]),
        ]
