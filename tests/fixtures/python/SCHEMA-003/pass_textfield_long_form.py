"""Fixture for SCHEMA-003: TextField for body/description columns is fine -- no short-name pattern."""

from django.db import models


class Article(models.Model):
    body = models.TextField()
    description = models.TextField()
    notes = models.TextField()
