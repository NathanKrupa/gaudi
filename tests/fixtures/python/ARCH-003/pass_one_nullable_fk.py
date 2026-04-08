"""Fixture for ARCH-003: a single nullable FK is below the >= 2 threshold."""

from django.db import models


class Activity(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey("User", null=True, on_delete=models.SET_NULL)
    order = models.ForeignKey("Order", on_delete=models.CASCADE)
