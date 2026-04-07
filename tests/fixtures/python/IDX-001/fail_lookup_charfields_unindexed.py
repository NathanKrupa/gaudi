"""Fixture for IDX-001: lookup-named CharFields without db_index."""

from django.db import models


class Customer(models.Model):
    email = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    api_key = models.CharField(max_length=64)
