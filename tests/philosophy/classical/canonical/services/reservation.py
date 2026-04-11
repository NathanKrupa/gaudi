"""
The reservation service: atomically reserves inventory for a validated order.

The atomicity guarantee lives at the repository layer — this service's
job is to translate the validated line items into a repository call
and to generate a reservation id on success. The actual locking or
conditional-update logic for a real storage backend would be inside
the repository implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain.models import LineItem, Product
from ..infrastructure.repositories import InventoryRepository, ReservationIdGenerator


@dataclass(frozen=True)
class ReservationSuccess:
    """An atomic reservation that succeeded."""

    reservation_id: str


@dataclass(frozen=True)
class ReservationFailure:
    """An atomic reservation that failed; no state was changed."""

    reason: str


ReservationResult = ReservationSuccess | ReservationFailure


class ReservationService:
    """Atomically reserves inventory for the line items of a validated order."""

    def __init__(
        self,
        inventory: InventoryRepository,
        id_generator: ReservationIdGenerator,
    ) -> None:
        self._inventory = inventory
        self._ids = id_generator

    def reserve(self, resolved_items: tuple[tuple[Product, LineItem], ...]) -> ReservationResult:
        line_items = [line for _, line in resolved_items]
        if self._inventory.reserve_all(line_items):
            return ReservationSuccess(reservation_id=self._ids.next())
        return ReservationFailure(reason="Inventory reservation could not be completed")
