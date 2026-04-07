"""Fixture for SCHEMA-002: 6-column model with 4 nullable columns (ratio 0.67)."""

from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    phone = models.CharField(max_length=50, null=True)
    fax = models.CharField(max_length=50, null=True)
    secondary_email = models.CharField(max_length=200, null=True)
    notes = models.CharField(max_length=2000, null=True)
