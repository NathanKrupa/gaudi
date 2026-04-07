"""Fixture for IDX-001: lookup fields with db_index or unique are fine."""

from django.db import models


class Customer(models.Model):
    email = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, db_index=True)
    api_key = models.CharField(max_length=64, db_index=True)
