"""Fixture for SEC-001: Meta defines an explicit permissions tuple."""

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ["-name"]
        permissions = (("approve_order", "Can approve order"),)
