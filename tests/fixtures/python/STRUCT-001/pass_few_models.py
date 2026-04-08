"""Fixture for STRUCT-001: a small models file (well under both thresholds)."""

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=200)


class Customer(models.Model):
    name = models.CharField(max_length=200)
