"""Fixture for SCHEMA-001: transactional model with no timestamp columns."""

from django.db import models


class Order(models.Model):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    amount = models.IntegerField()
    status = models.CharField(max_length=16)
