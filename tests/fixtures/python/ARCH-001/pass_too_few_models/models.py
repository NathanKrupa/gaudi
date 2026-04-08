"""Fixture for ARCH-001: 2 models is below the >= 3 threshold."""

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=200)
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)


class Customer(models.Model):
    name = models.CharField(max_length=200)
