"""Fixture for SCHEMA-001: reference/lookup model without timestamps.

A model with no ForeignKey and no mutable-state fields (status, is_active)
is reference data that doesn't need audit timestamps.
"""

from django.db import models


class Product(models.Model):
    sku = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    max_per_order = models.PositiveIntegerField()
    category = models.CharField(max_length=64)
