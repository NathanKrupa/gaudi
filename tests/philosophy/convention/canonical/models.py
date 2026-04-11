"""
Django models for the Convention reference exemplar.

The fat-model pattern is the blessed Django way: business logic
lives on the model and its Manager. There is no OrderService class
between the view and the model because extracting one would be
fighting the framework — the framework's ORM manager IS the service
layer. See docs/philosophy/convention.md catechism #6 ("integrate,
do not wrap").

Every model has:
- Constants on the class for its status choices (Django idiom)
- A custom Manager with domain-named query methods
- ``class Meta`` permissions / ordering where meaningful
- ``__str__`` for admin readability

Order.objects.place_order() is the composition root of the
pipeline. It runs inside a transaction.atomic() block and uses
F() expressions to avoid race conditions on inventory. Under a
real concurrent Django deployment those F() updates would be
the production-correct reservation primitive.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone


class CustomerStanding(models.TextChoices):
    GOOD = "good", "Good"
    HOLD = "hold", "On Hold"
    BANNED = "banned", "Banned"


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    REJECTED = "rejected", "Rejected"


class CustomerManager(models.Manager["Customer"]):
    def good_standing(self) -> models.QuerySet["Customer"]:
        return self.filter(standing=CustomerStanding.GOOD)


class Customer(models.Model):
    customer_id = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    email = models.EmailField()
    standing = models.CharField(
        max_length=16,
        choices=CustomerStanding.choices,
        default=CustomerStanding.GOOD,
    )
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2)

    objects = CustomerManager()

    class Meta:
        ordering = ["customer_id"]

    def __str__(self) -> str:
        return f"{self.customer_id} ({self.name})"

    @property
    def may_place_orders(self) -> bool:
        return self.standing == CustomerStanding.GOOD


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

    class Meta:
        ordering = ["sku"]

    def __str__(self) -> str:
        return f"{self.sku} ({self.name})"


class InventoryLevelManager(models.Manager["InventoryLevel"]):
    def available(self, sku: str) -> int:
        level = self.filter(sku=sku).first()
        if level is None:
            return 0
        return level.on_hand - level.reserved

    @transaction.atomic
    def reserve_many(self, requested: list[tuple[str, int]]) -> bool:
        """Atomically reserve stock for a list of (sku, quantity) pairs.

        Uses ``select_for_update`` to lock the relevant rows, then
        an F() expression to increment ``reserved`` in a single SQL
        statement per sku. Returns True iff every requested line
        could be satisfied.
        """
        skus = [sku for sku, _qty in requested]
        locked = {level.sku: level for level in self.select_for_update().filter(sku__in=skus)}
        for sku, qty in requested:
            level = locked.get(sku)
            if level is None or (level.on_hand - level.reserved) < qty:
                return False
        for sku, qty in requested:
            self.filter(sku=sku).update(reserved=F("reserved") + qty)
        return True


class InventoryLevel(models.Model):
    sku = models.CharField(max_length=32, unique=True)
    on_hand = models.PositiveIntegerField()
    reserved = models.PositiveIntegerField(default=0)

    objects = InventoryLevelManager()

    class Meta:
        ordering = ["sku"]
        verbose_name = "Inventory level"

    def __str__(self) -> str:
        return f"{self.sku}: {self.on_hand} on hand, {self.reserved} reserved"


class PromoCode(models.Model):
    code = models.CharField(max_length=32, unique=True)
    percent_off = models.PositiveSmallIntegerField()
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.percent_off}% off)"

    def is_active(self) -> bool:
        return self.expires_at > timezone.now()


class OrderManager(models.Manager["Order"]):
    """The composition root of the order-processing pipeline.

    ``place_order`` is where validation, pricing, and reservation
    all happen. Under the Convention discipline this lives on the
    manager rather than in a separate service class, because the
    manager IS the blessed service layer.
    """

    @transaction.atomic
    def place_order(
        self,
        *,
        customer_id: str,
        line_items: list[dict[str, object]],
        promo_code: str | None,
        shipping_address: str,
        order_id: str,
    ) -> "Order":
        customer = Customer.objects.filter(customer_id=customer_id).first()
        if customer is None:
            return self._reject(
                order_id, customer_id, shipping_address, f"Unknown customer {customer_id}"
            )

        if not customer.may_place_orders:
            return self._reject(
                order_id,
                customer_id,
                shipping_address,
                f"Customer {customer.customer_id} standing is "
                f"{customer.standing}; may not place orders",
            )

        resolved: list[tuple[Product, int]] = []
        for raw in line_items:
            sku = str(raw["sku"])
            qty = int(raw["quantity"])  # type: ignore[arg-type]
            product = Product.objects.by_sku(sku)
            if product is None:
                return self._reject(
                    order_id, customer_id, shipping_address, f"Unknown product {sku}"
                )
            if qty > product.max_per_order:
                return self._reject(
                    order_id,
                    customer_id,
                    shipping_address,
                    f"Line item {sku} quantity {qty} exceeds max_per_order {product.max_per_order}",
                )
            resolved.append((product, qty))

        subtotal = sum(
            (p.unit_price * qty for p, qty in resolved),
            start=Decimal(0),
        )
        discount = Decimal(0)
        if promo_code:
            promo = PromoCode.objects.filter(code=promo_code).first()
            if promo and promo.is_active():
                discount = (subtotal * Decimal(promo.percent_off) / Decimal(100)).quantize(
                    Decimal("0.01")
                )
        final_price = subtotal - discount + Decimal(settings.SHIPPING_FEE)

        if final_price > customer.credit_limit:
            return self._reject(
                order_id,
                customer_id,
                shipping_address,
                f"Final price {final_price} exceeds customer "
                f"{customer.customer_id} credit limit {customer.credit_limit}",
            )

        insufficient = [
            p.sku for p, qty in resolved if InventoryLevel.objects.available(p.sku) < qty
        ]
        if insufficient:
            return self._reject(
                order_id,
                customer_id,
                shipping_address,
                f"Insufficient inventory for: {', '.join(insufficient)}",
            )

        if not InventoryLevel.objects.reserve_many([(p.sku, qty) for p, qty in resolved]):
            return self._reject(
                order_id,
                customer_id,
                shipping_address,
                "Inventory reservation could not be completed",
            )

        order = self.create(
            order_id=order_id,
            customer=customer,
            shipping_address=shipping_address,
            status=OrderStatus.CONFIRMED,
            final_price=final_price,
            rejection_reason="",
        )
        for product, qty in resolved:
            OrderLine.objects.create(order=order, product=product, quantity=qty)
        Notification.objects.create(
            order_id=order_id,
            status=OrderStatus.CONFIRMED,
            final_price=final_price,
            rejection_reason="",
        )
        return order

    def _reject(
        self,
        order_id: str,
        customer_id: str,
        shipping_address: str,
        reason: str,
    ) -> "Order":
        customer = Customer.objects.filter(customer_id=customer_id).first()
        order = self.create(
            order_id=order_id,
            customer=customer,
            shipping_address=shipping_address,
            status=OrderStatus.REJECTED,
            final_price=None,
            rejection_reason=reason,
        )
        Notification.objects.create(
            order_id=order_id,
            status=OrderStatus.REJECTED,
            final_price=None,
            rejection_reason=reason,
        )
        return order


class Order(models.Model):
    order_id = models.CharField(max_length=32, unique=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )
    shipping_address = models.CharField(max_length=500)
    status = models.CharField(
        max_length=16,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
    )
    final_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrderManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order_id} ({self.status})"


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["id"]


class Notification(models.Model):
    order_id = models.CharField(max_length=32, db_index=True)
    status = models.CharField(max_length=16, choices=OrderStatus.choices)
    final_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True, default="")
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self) -> str:
        return f"Notification for {self.order_id}: {self.status}"
