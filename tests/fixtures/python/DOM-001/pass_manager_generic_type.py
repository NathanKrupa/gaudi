"""Fixture for DOM-001: Manager with generic type annotation Manager["Model"].

When a Manager subclass uses the generic form ``models.Manager["Model"]``,
DOM-001 should still recognize it as a Manager and count its methods as
behavior belonging to the model.
"""

from django.db import models


class ProductManager(models.Manager["Product"]):
    def by_sku(self, sku: str) -> "Product | None":
        return self.filter(sku=sku).first()


class Product(models.Model):
    sku = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    max_per_order = models.PositiveIntegerField()
    category = models.CharField(max_length=64)

    objects = ProductManager()
