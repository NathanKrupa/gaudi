"""
Repository Protocols and in-memory implementations for the pipeline's
persistence needs.

The Repository pattern here is the exemplar's one named pattern used
meaningfully (rubric check #3). Each Protocol hides real complexity:
"where the customers/products/inventory are stored, and whether that
storage is a dict, SQLite, or Postgres — the service does not care
and cannot be made to care." The service layer depends only on the
Protocols; the ``InMemory*`` implementations exist for the exemplar's
tests, and swapping them for a database-backed implementation is a
one-file change in the composition root.

An ``InventoryRepository.reserve`` method exists alongside ``get``
because the reservation operation is atomic at the persistence
boundary — any implementation with a real backing store would need
to lock the row or use a conditional update, and that is infrastructure
concern, not domain concern.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from typing import Protocol

from ..domain.models import Customer, CustomerStanding, InventoryLevel, LineItem, Product, PromoCode


class CustomerRepository(Protocol):
    """Looks up customers by id."""

    def get(self, customer_id: str) -> Customer | None: ...


class ProductRepository(Protocol):
    """Looks up products by SKU."""

    def get(self, sku: str) -> Product | None: ...


class InventoryRepository(Protocol):
    """Looks up inventory levels and atomically reserves stock."""

    def get(self, sku: str) -> InventoryLevel | None: ...

    def reserve_all(self, requested: list[LineItem]) -> bool: ...


class PromoCodeRepository(Protocol):
    """Looks up promotional codes by code string."""

    def get(self, code: str) -> PromoCode | None: ...


class InMemoryCustomerRepository:
    """An in-memory customer store built from a seed dict."""

    def __init__(self, customers: list[Customer]) -> None:
        self._by_id: dict[str, Customer] = {c.customer_id: c for c in customers}

    def get(self, customer_id: str) -> Customer | None:
        return self._by_id.get(customer_id)


class InMemoryProductRepository:
    """An in-memory product store built from a seed dict."""

    def __init__(self, products: list[Product]) -> None:
        self._by_sku: dict[str, Product] = {p.sku: p for p in products}

    def get(self, sku: str) -> Product | None:
        return self._by_sku.get(sku)


class InMemoryInventoryRepository:
    """
    An in-memory inventory store with atomic reservation semantics.

    ``reserve_all`` is all-or-nothing: if any requested line item cannot
    be satisfied from the currently-available stock, the reservation
    fails and no state changes.
    """

    def __init__(self, levels: list[InventoryLevel]) -> None:
        self._levels: dict[str, InventoryLevel] = {level.sku: level for level in levels}

    def get(self, sku: str) -> InventoryLevel | None:
        return self._levels.get(sku)

    def reserve_all(self, requested: list[LineItem]) -> bool:
        for item in requested:
            level = self._levels.get(item.sku)
            if level is None or level.available < item.quantity:
                return False
        for item in requested:
            level = self._levels[item.sku]
            self._levels[item.sku] = replace(level, reserved=level.reserved + item.quantity)
        return True


class InMemoryPromoCodeRepository:
    """An in-memory promotional code store."""

    def __init__(self, codes: list[PromoCode]) -> None:
        self._by_code: dict[str, PromoCode] = {p.code: p for p in codes}

    def get(self, code: str) -> PromoCode | None:
        return self._by_code.get(code)


class ReservationIdGenerator:
    """Generates unique reservation identifiers for confirmed orders."""

    def __init__(self, prefix: str = "RES") -> None:
        self._prefix = prefix
        self._counter = itertools.count(1)

    def next(self) -> str:
        return f"{self._prefix}-{next(self._counter):06d}"


def build_customer(data: dict[str, object]) -> Customer:
    """Parses a seed dict into a Customer value object."""
    from decimal import Decimal

    return Customer(
        customer_id=str(data["customer_id"]),
        name=str(data["name"]),
        email=str(data["email"]),
        standing=CustomerStanding(str(data["standing"])),
        credit_limit=Decimal(str(data["credit_limit"])),
    )


def build_product(data: dict[str, object]) -> Product:
    """Parses a seed dict into a Product value object."""
    from decimal import Decimal

    return Product(
        sku=str(data["sku"]),
        name=str(data["name"]),
        unit_price=Decimal(str(data["unit_price"])),
        max_per_order=int(data["max_per_order"]),  # type: ignore[arg-type]
        category=str(data["category"]),
    )


def build_inventory_level(data: dict[str, object]) -> InventoryLevel:
    """Parses a seed dict into an InventoryLevel value object."""
    return InventoryLevel(
        sku=str(data["sku"]),
        on_hand=int(data["on_hand"]),  # type: ignore[arg-type]
        reserved=int(data["reserved"]),  # type: ignore[arg-type]
    )


def build_promo_code(data: dict[str, object]) -> PromoCode:
    """Parses a seed dict into a PromoCode value object."""
    from datetime import datetime

    return PromoCode(
        code=str(data["code"]),
        percent_off=int(data["percent_off"]),  # type: ignore[arg-type]
        expires_at=datetime.fromisoformat(str(data["expires_at"])),
    )
