"""Fixture for SEC-001: ordinary domain model without explicit permissions.

Non-security-sensitive models (Order, Product, etc.) don't need explicit
Meta.permissions — Django's auto-generated add/change/delete/view
permissions are sufficient.
"""

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ["-name"]
