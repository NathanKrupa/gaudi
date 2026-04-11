"""
The validation service: determines whether an order can proceed to pricing.

A successful validation result carries the resolved ``Customer`` and the
resolved ``(Product, quantity)`` pairs, so the pricing service never
needs to touch a repository. This is deliberate: pricing is a pure
computation over resolved domain values, and pushing the I/O to the
validation boundary lets the rest of the pipeline treat pricing as a
pure step.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import Customer, LineItem, Order, Product
from ..infrastructure.repositories import CustomerRepository, InventoryRepository, ProductRepository


@dataclass(frozen=True)
class ValidationSuccess:
    """A valid order, with its dependencies resolved for downstream stages."""

    customer: Customer
    resolved_items: tuple[tuple[Product, LineItem], ...]


@dataclass(frozen=True)
class ValidationFailure:
    """A rejected order, carrying a human-readable reason."""

    reason: str


ValidationResult = ValidationSuccess | ValidationFailure


class ValidationService:
    """Decides whether an order can proceed to the pricing stage."""

    def __init__(
        self,
        customers: CustomerRepository,
        products: ProductRepository,
        inventory: InventoryRepository,
    ) -> None:
        self._customers = customers
        self._products = products
        self._inventory = inventory

    def validate(self, order: Order) -> ValidationResult:
        customer_or_failure = self._resolve_customer(order.customer_id)
        if isinstance(customer_or_failure, ValidationFailure):
            return customer_or_failure

        resolved_or_failure = self._resolve_line_items(order.line_items)
        if isinstance(resolved_or_failure, ValidationFailure):
            return resolved_or_failure

        insufficient = self._insufficient_inventory(resolved_or_failure)
        if insufficient:
            names = ", ".join(insufficient)
            return ValidationFailure(reason=f"Insufficient inventory for: {names}")

        return ValidationSuccess(
            customer=customer_or_failure,
            resolved_items=tuple(resolved_or_failure),
        )

    def _resolve_customer(self, customer_id: str) -> Customer | ValidationFailure:
        customer = self._customers.get(customer_id)
        if customer is None:
            return ValidationFailure(reason=f"Unknown customer {customer_id}")
        if not customer.may_place_orders:
            return ValidationFailure(
                reason=(
                    f"Customer {customer.customer_id} standing is "
                    f"{customer.standing.value}; may not place orders"
                )
            )
        return customer

    def _resolve_line_items(
        self, line_items: tuple[LineItem, ...]
    ) -> list[tuple[Product, LineItem]] | ValidationFailure:
        resolved: list[tuple[Product, LineItem]] = []
        for line in line_items:
            product = self._products.get(line.sku)
            if product is None:
                return ValidationFailure(reason=f"Unknown product {line.sku}")
            if line.quantity > product.max_per_order:
                return ValidationFailure(
                    reason=(
                        f"Line item {line.sku} quantity {line.quantity} "
                        f"exceeds max_per_order {product.max_per_order}"
                    )
                )
            resolved.append((product, line))
        return resolved

    def _insufficient_inventory(self, resolved: list[tuple[Product, LineItem]]) -> list[str]:
        """Returns the SKUs whose requested quantity exceeds available stock."""
        shortfalls: list[str] = []
        for product, line in resolved:
            level = self._inventory.get(product.sku)
            if level is None or level.available < line.quantity:
                shortfalls.append(product.sku)
        return shortfalls
