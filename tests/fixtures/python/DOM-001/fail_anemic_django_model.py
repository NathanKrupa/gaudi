# Fixture for DOM-001: AnemicDomainModel
# Django model with 8 fields and zero behavior — pure data bag.
from django.db import models


class Invoice(models.Model):
    customer_name = models.CharField(max_length=200)
    customer_email = models.CharField(max_length=200)
    amount_cents = models.IntegerField()
    tax_cents = models.IntegerField()
    discount_cents = models.IntegerField()
    currency = models.CharField(max_length=3)
    issued_at = models.DateTimeField()
    due_at = models.DateTimeField()

    class Meta:
        ordering = ["-issued_at"]
