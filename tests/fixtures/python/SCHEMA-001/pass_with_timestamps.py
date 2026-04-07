"""Fixture for SCHEMA-001: a model with created_at and updated_at columns."""

from django.db import models


class Order(models.Model):
    customer = models.CharField(max_length=200)
    amount = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
