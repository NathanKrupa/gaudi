"""Fixture for ARCH-002: a normal-width model below the 15 column threshold."""

from django.db import models


class Customer(models.Model):
    name = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    phone = models.CharField(max_length=50)
