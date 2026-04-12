"""Fixture for SEC-001: security-sensitive model with Meta but no permissions."""

from django.db import models


class UserAccount(models.Model):
    name = models.CharField(max_length=200)

    class Meta:
        ordering = ["-name"]
