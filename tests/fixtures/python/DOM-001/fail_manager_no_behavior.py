# Fixture for DOM-001: Manager exists but has no business methods — still anemic.
from django.db import models


class OrderManager(models.Manager):
    pass


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
