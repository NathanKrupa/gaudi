"""Fixture for SEC-001: a model with no Meta class is out of scope.

The rule keys on `has_meta and 'permissions' not in meta_options`. A model
without any Meta inner class doesn't trip the rule -- the absence of a Meta
declaration is documented as out of scope.
"""

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=200)
