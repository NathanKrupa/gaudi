"""Fixture for SCHEMA-001: through tables (< 2 columns) are exempt."""

from django.db import models


class OrderTag(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE)
