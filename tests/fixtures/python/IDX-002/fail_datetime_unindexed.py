"""Fixture for IDX-002: DateTimeFields without db_index that aren't auto-timestamps."""

from django.db import models


class Event(models.Model):
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    published_on = models.DateField()
