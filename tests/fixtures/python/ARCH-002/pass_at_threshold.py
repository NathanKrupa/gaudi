"""Fixture for ARCH-002: exactly 15 columns is at the threshold (not above)."""

from django.db import models


class Customer(models.Model):
    f1 = models.CharField(max_length=200)
    f2 = models.CharField(max_length=200)
    f3 = models.CharField(max_length=200)
    f4 = models.CharField(max_length=200)
    f5 = models.CharField(max_length=200)
    f6 = models.CharField(max_length=200)
    f7 = models.CharField(max_length=200)
    f8 = models.CharField(max_length=200)
    f9 = models.CharField(max_length=200)
    f10 = models.CharField(max_length=200)
    f11 = models.CharField(max_length=200)
    f12 = models.CharField(max_length=200)
    f13 = models.CharField(max_length=200)
    f14 = models.CharField(max_length=200)
    f15 = models.CharField(max_length=200)
