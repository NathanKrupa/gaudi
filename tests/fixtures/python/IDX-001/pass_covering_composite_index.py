"""Fixture for IDX-001: a covering composite index serves the lookup column.

``status`` leads the composite index ``(status, created_at)``, so a query
filtering on ``status`` is already served. A standalone db_index would only
duplicate coverage, so IDX-001 must not fire on ``status``.
"""

from django.db import models


class Order(models.Model):
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]
