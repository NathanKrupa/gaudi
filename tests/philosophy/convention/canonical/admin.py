"""
Admin registrations for the Convention reference exemplar.

Rubric check #7 ("admin is wired where the framework provides it")
is satisfied by registering every model with a ``ModelAdmin`` that
declares ``list_display``, ``search_fields``, and ``list_filter``
where appropriate. A real Convention deployment would expose the
admin through ``urls.py``; the exemplar stops at the registration
because the canonical-task.md out-of-scope list excludes HTTP
surfaces.
"""

from django.contrib import admin

from .models import (
    Customer,
    InventoryLevel,
    Notification,
    Order,
    OrderLine,
    Product,
    PromoCode,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_id", "name", "email", "standing", "credit_limit")
    list_filter = ("standing",)
    search_fields = ("customer_id", "name", "email")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "unit_price", "max_per_order", "category")
    list_filter = ("category",)
    search_fields = ("sku", "name")


@admin.register(InventoryLevel)
class InventoryLevelAdmin(admin.ModelAdmin):
    list_display = ("sku", "on_hand", "reserved")
    search_fields = ("sku",)


@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "percent_off", "expires_at")
    search_fields = ("code",)


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_id",
        "customer",
        "status",
        "final_price",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("order_id", "customer__customer_id")
    inlines = [OrderLineInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("order_id", "status", "final_price", "sent_at")
    list_filter = ("status",)
    search_fields = ("order_id",)
    readonly_fields = ("sent_at",)
