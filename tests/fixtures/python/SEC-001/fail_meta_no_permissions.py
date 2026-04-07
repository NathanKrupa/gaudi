"""Fixture for SEC-001: Django model with a Meta class but no permissions key."""

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ["-name"]
