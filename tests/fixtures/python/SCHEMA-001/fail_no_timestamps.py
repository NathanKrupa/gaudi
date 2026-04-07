"""Fixture for SCHEMA-001: a model with no created/updated timestamp columns."""

from django.db import models


class Order(models.Model):
    customer = models.CharField(max_length=200)
    amount = models.IntegerField()
