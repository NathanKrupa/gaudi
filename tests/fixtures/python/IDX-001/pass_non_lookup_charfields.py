"""Fixture for IDX-001: CharFields whose names are not lookup-shaped don't need indexes."""

from django.db import models


class Note(models.Model):
    title = models.CharField(max_length=200)
    body = models.CharField(max_length=2000)
    author_display = models.CharField(max_length=200)
