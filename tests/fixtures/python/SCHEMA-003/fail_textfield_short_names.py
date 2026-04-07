"""Fixture for SCHEMA-003: TextField used for fields with short-name patterns."""

from django.db import models


class Item(models.Model):
    name = models.TextField()
    sku = models.TextField()
    status = models.TextField()
