# Fixture for DOM-001: a Django model with behavior must NOT trigger.
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

    def total_cents(self) -> int:
        return self.amount_cents + self.tax_cents - self.discount_cents

    def is_overdue(self, now) -> bool:
        return self.due_at < now
