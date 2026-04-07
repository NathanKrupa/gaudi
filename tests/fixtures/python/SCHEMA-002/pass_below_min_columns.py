"""Fixture for SCHEMA-002: a 5-column model is below MIN_COLUMNS, exempt regardless of ratio."""

from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200, null=True)
    phone = models.CharField(max_length=50, null=True)
    fax = models.CharField(max_length=50, null=True)
    notes = models.CharField(max_length=2000, null=True)
