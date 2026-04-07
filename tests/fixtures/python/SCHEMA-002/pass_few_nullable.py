"""Fixture for SCHEMA-002: 6-column model with only 1 nullable column."""

from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    phone = models.CharField(max_length=50)
    address = models.CharField(max_length=500)
    city = models.CharField(max_length=100)
    notes = models.CharField(max_length=2000, null=True)
