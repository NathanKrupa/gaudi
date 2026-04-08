"""Fixture for DJ-ARCH-003: model method that only computes / persists."""

from django.db import models


class Order(models.Model):
    total = models.IntegerField()
    discount = models.IntegerField(default=0)

    def net_total(self) -> int:
        return self.total - self.discount
