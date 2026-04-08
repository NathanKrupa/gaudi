"""Fixture for ARCH-003: model with two nullable ForeignKeys."""

from django.db import models


class Activity(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey("User", null=True, on_delete=models.SET_NULL)
    order = models.ForeignKey("Order", null=True, on_delete=models.SET_NULL)
