"""Fixture for ARCH-003: an entity with real fields and two optional FKs.

A first-class entity (it carries its own ``name`` field) that happens to have
two optional relationships is NOT a missing join table — it is a by-design
model. ARCH-003 must not fire.
"""

from django.db import models


class Activity(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey("User", null=True, on_delete=models.SET_NULL)
    order = models.ForeignKey("Order", null=True, on_delete=models.SET_NULL)
