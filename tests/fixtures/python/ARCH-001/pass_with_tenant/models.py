"""Fixture for ARCH-001: same shape but with a tenant ForeignKey."""

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=200)
    tenant = models.ForeignKey("Tenant", on_delete=models.CASCADE)
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)


class Customer(models.Model):
    name = models.CharField(max_length=200)
    tenant = models.ForeignKey("Tenant", on_delete=models.CASCADE)


class Tenant(models.Model):
    name = models.CharField(max_length=200)
