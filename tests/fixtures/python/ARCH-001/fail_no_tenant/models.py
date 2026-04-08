"""Fixture for ARCH-001: 3 related models with no tenant column."""

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=200)
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)


class Customer(models.Model):
    name = models.CharField(max_length=200)
    address = models.ForeignKey("Address", on_delete=models.CASCADE)


class Address(models.Model):
    street = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
