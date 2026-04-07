# Fixture for DOM-003: ActiveRecordMisuse.
# Django model whose method calls an external HTTP service directly.
import requests
from django.db import models


class Webhook(models.Model):
    url = models.URLField()
    payload = models.JSONField()

    def fire(self):
        return requests.post(self.url, json=self.payload, timeout=5)
