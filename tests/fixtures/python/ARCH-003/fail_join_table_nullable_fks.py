"""Fixture for ARCH-003: a join-table-shaped model with only nullable FKs.

The model's only fields are ForeignKeys, so it is shaped like a join table —
yet both are nullable, so a row can exist while recording no association. That
is the genuine smell ARCH-003 names.
"""

from django.db import models


class Enrollment(models.Model):
    student = models.ForeignKey("Student", null=True, on_delete=models.SET_NULL)
    course = models.ForeignKey("Course", null=True, on_delete=models.SET_NULL)
