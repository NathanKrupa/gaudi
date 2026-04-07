# Fixture for DOM-003: a model whose methods only compute/persist must NOT trigger.
from django.db import models


class Invoice(models.Model):
    amount_cents = models.IntegerField()
    tax_cents = models.IntegerField()
    discount_cents = models.IntegerField()

    def total_cents(self) -> int:
        return self.amount_cents + self.tax_cents - self.discount_cents
