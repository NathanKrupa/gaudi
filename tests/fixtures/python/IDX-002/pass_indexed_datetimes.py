"""Fixture for IDX-002: DateTime/Date fields with db_index are fine."""

from django.db import models


class Event(models.Model):
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    published_on = models.DateField(db_index=True)
