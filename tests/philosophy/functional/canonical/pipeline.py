"""
The pure-function pipeline for the canonical order-processing task.

Every function in this module is a pure transformation: given the
same inputs, it produces the same outputs and has no observable
effect on anything else. Errors are returned as ``Err`` values, not
raised. Inventory is updated by returning a new mapping, never by
mutating the passed-in one. ``process_order`` composes the smaller
functions via straight-line application and returns both the
terminal outcome and a new ``World`` with the reservation applied.

The caller's responsibility: thread the returned ``new_world`` into
the next ``process_order`` call. This is the "functional core,
imperative shell" pattern — the core is pure; the caller (or a thin
outer layer) manages the sequence.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from typing import Mapping

from .models import (
    Customer,
    CustomerStanding,
    InventoryLevel,
    LineItem,
    Order,
    OrderStatus,
    Outcome,
    Product,
    PromoCode,
    World,
)
from .result import Err, Ok


def validate_customer(
    customers: Mapping[str, Customer], customer_id: str
) -> Ok[Customer] | Err[str]:
    """Return the customer if they exist and may place orders."""
    customer = customers.get(customer_id)
    if customer is None:
        return Err(f"Unknown customer {customer_id}")
    if customer.standing is not CustomerStanding.GOOD:
        return Err(
            f"Customer {customer.customer_id} standing is "
            f"{customer.standing.value}; may not place orders"
        )
    return Ok(customer)


def resolve_line(
    products: Mapping[str, Product], line: LineItem
) -> Ok[tuple[Product, LineItem]] | Err[str]:
    """Resolve one line to its product, checking max_per_order."""
    product = products.get(line.sku)
    if product is None:
        return Err(f"Unknown product {line.sku}")
    if line.quantity > product.max_per_order:
        return Err(
            f"Line item {line.sku} quantity {line.quantity} "
            f"exceeds max_per_order {product.max_per_order}"
        )
    return Ok((product, line))


def resolve_lines(
    products: Mapping[str, Product], line_items: tuple[LineItem, ...]
) -> Ok[tuple[tuple[Product, LineItem], ...]] | Err[str]:
    """Resolve every line item. Returns Err at the first invalid line."""
    resolved: list[tuple[Product, LineItem]] = []
    for line in line_items:
        result = resolve_line(products, line)
        if isinstance(result, Err):
            return result
        resolved.append(result.value)
    return Ok(tuple(resolved))


def find_insufficient_skus(
    inventory: Mapping[str, InventoryLevel],
    resolved: tuple[tuple[Product, LineItem], ...],
) -> tuple[str, ...]:
    """Return the SKUs whose requested quantity exceeds available stock."""
    return tuple(
        product.sku
        for product, line in resolved
        if _available(inventory.get(product.sku)) < line.quantity
    )


def _available(level: InventoryLevel | None) -> int:
    """Return the available (on-hand minus reserved) stock for a level, zero if absent."""
    if level is None:
        return 0
    return level.on_hand - level.reserved


def _promo_is_active(promo: PromoCode, now: datetime) -> bool:
    """Return True iff the promo has not yet expired as of ``now``."""
    return now < promo.expires_at


def compute_subtotal(resolved: tuple[tuple[Product, LineItem], ...]) -> Decimal:
    """Sum of unit_price × quantity across all resolved lines."""
    return sum(
        (product.unit_price * line.quantity for product, line in resolved),
        start=Decimal(0),
    )


def compute_discount(
    subtotal: Decimal,
    promo_code: str | None,
    promo_codes: Mapping[str, PromoCode],
    now: datetime,
) -> Decimal:
    """Return the discount amount, or zero if promo is missing/expired."""
    if promo_code is None:
        return Decimal(0)
    promo = promo_codes.get(promo_code)
    if promo is None or not _promo_is_active(promo, now):
        return Decimal(0)
    return (subtotal * Decimal(promo.percent_off) / Decimal(100)).quantize(Decimal("0.01"))


def compute_final_price(
    resolved: tuple[tuple[Product, LineItem], ...],
    promo_code: str | None,
    world: World,
) -> Decimal:
    """Compute subtotal minus discount plus shipping."""
    subtotal = compute_subtotal(resolved)
    discount = compute_discount(subtotal, promo_code, world.promo_codes, world.now)
    return subtotal - discount + world.shipping_fee


def reserve_inventory(
    inventory: Mapping[str, InventoryLevel],
    resolved: tuple[tuple[Product, LineItem], ...],
) -> Mapping[str, InventoryLevel]:
    """Return a NEW inventory mapping with reservations applied.

    Caller must have pre-validated availability — this function
    trusts its input and does not re-check. Nothing is mutated: the
    returned mapping is a fresh dict whose touched levels are fresh
    frozen dataclass instances constructed via ``dataclasses.replace``.
    """
    delta: dict[str, int] = {}
    for _product, line in resolved:
        delta[line.sku] = delta.get(line.sku, 0) + line.quantity
    return {
        sku: (replace(level, reserved=level.reserved + delta[sku]) if sku in delta else level)
        for sku, level in inventory.items()
    }


def confirmed(order: Order, final_price: Decimal, reservation_id: str) -> Outcome:
    """Build a terminal Outcome for a confirmed order."""
    return Outcome(
        order_id=order.order_id,
        status=OrderStatus.CONFIRMED,
        final_price=final_price,
        reservation_id=reservation_id,
        rejection_reason=None,
    )


def rejected(order: Order, reason: str) -> Outcome:
    """Build a terminal Outcome for a rejected order."""
    return Outcome(
        order_id=order.order_id,
        status=OrderStatus.REJECTED,
        final_price=None,
        reservation_id=None,
        rejection_reason=reason,
    )


def process_order(order: Order, world: World, reservation_id: str) -> tuple[Outcome, World]:
    """Compose the full pipeline for one order.

    Returns ``(outcome, new_world)``. The input ``world`` is never
    mutated. On a confirmed order, ``new_world.inventory`` reflects
    the applied reservation; on rejection, ``new_world`` is returned
    unchanged.
    """
    customer_result = validate_customer(world.customers, order.customer_id)
    if isinstance(customer_result, Err):
        return rejected(order, customer_result.error), world
    customer = customer_result.value

    lines_result = resolve_lines(world.products, order.line_items)
    if isinstance(lines_result, Err):
        return rejected(order, lines_result.error), world
    resolved = lines_result.value

    insufficient = find_insufficient_skus(world.inventory, resolved)
    if insufficient:
        return rejected(order, f"Insufficient inventory for: {', '.join(insufficient)}"), world

    final_price = compute_final_price(resolved, order.promo_code, world)

    if final_price > customer.credit_limit:
        return (
            rejected(
                order,
                f"Final price {final_price} exceeds customer "
                f"{customer.customer_id} credit limit {customer.credit_limit}",
            ),
            world,
        )

    new_inventory = reserve_inventory(world.inventory, resolved)
    new_world = replace(world, inventory=new_inventory)
    return confirmed(order, final_price, reservation_id), new_world
