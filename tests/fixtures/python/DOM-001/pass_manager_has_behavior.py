# Fixture for DOM-001: model with behavior on a Manager subclass must NOT trigger.
from django.db import models


class OrderManager(models.Manager):
    def pending(self):
        return self.filter(status="pending")

    def total_revenue(self):
        return self.aggregate(total=models.Sum("amount_cents"))["total"]


class Order(models.Model):
    customer_name = models.CharField(max_length=200)
    customer_email = models.CharField(max_length=200)
    amount_cents = models.IntegerField()
    tax_cents = models.IntegerField()
    discount_cents = models.IntegerField()
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField()

    objects = OrderManager()
