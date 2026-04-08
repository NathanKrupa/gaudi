"""Fixture for DJ-ARCH-003: model method making external calls."""

from django.db import models
import requests


class Order(models.Model):
    total = models.IntegerField()

    def notify_warehouse(self):
        requests.post("https://warehouse.example.com/orders", json={"id": self.id})
        self.save()
