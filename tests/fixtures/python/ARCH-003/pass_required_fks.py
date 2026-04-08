"""Fixture for ARCH-003: ForeignKeys without null=True don't count toward sprawl."""

from django.db import models


class Activity(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    order = models.ForeignKey("Order", on_delete=models.CASCADE)
