"""Fixture for SCHEMA-001: transactional model with FK but no timestamps.

A model with a ForeignKey relationship is transactional data that
should have created_at/updated_at audit columns.
"""

from django.db import models


class OrderLine(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE)
    product = models.ForeignKey("Product", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
