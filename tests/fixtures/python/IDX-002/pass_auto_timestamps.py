"""Fixture for IDX-002: auto-timestamp columns are exempt."""

from django.db import models


class Event(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    modified_at = models.DateTimeField(auto_now=True)
