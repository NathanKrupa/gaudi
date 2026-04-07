"""Fixture for SCHEMA-003: short-name fields use CharField with max_length, the canonical escape."""

from django.db import models


class Item(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64)
    status = models.CharField(max_length=32)
