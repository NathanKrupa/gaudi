"""
The composition root and pipeline orchestrator for the Classical exemplar.

``OrderPipeline`` wires the four services together and drives an order
through validation, pricing, the credit-limit check, reservation, and
notification. It receives its services via constructor injection —
the pipeline itself does not know how to construct a
``ValidationService`` or a ``ReservationService``.

The factory function ``build_pipeline`` is the one place in the exemplar
where concrete implementations are chosen. A production deployment would
have a different composition root (one that wires SQL-backed
repositories and a real notification sender) and the rest of the
exemplar would be reused unchanged. This is the Classical school's
core claim: infrastructure is a detail, the domain kernel is stable,
and the composition root is the seam where one is bound to the other.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .domain.models import Order, OrderOutcome, OrderStatus
from .infrastructure.clock import Clock, FixedClock
from .infrastructure.repositories import (
    InMemoryCustomerRepository,
    InMemoryInventoryRepository,
    InMemoryProductRepository,
    InMemoryPromoCodeRepository,
    ReservationIdGenerator,
    build_customer,
    build_inventory_level,
    build_product,
    build_promo_code,
)
from .services.notification import InMemoryNotificationSender, NotificationService
from .services.pricing import PricingResult, PricingService
from .services.reservation import ReservationFailure, ReservationService, ReservationSuccess
from .services.validation import ValidationFailure, ValidationService


class OrderPipeline:
    """Orchestrates an order through the four processing stages to a terminal outcome."""

    def __init__(
        self,
        validation: ValidationService,
        pricing: PricingService,
        reservation: ReservationService,
        notification: NotificationService,
    ) -> None:
        self._validation = validation
        self._pricing = pricing
        self._reservation = reservation
        self._notification = notification

    def process(self, order: Order) -> OrderOutcome:
        validation_result = self._validation.validate(order)
        if isinstance(validation_result, ValidationFailure):
            return self._reject(order, validation_result.reason)

        customer = validation_result.customer
        resolved = validation_result.resolved_items

        pricing_result = self._pricing.compute(resolved, order.promo_code)
        if pricing_result.final_price > customer.credit_limit:
            return self._reject(
                order,
                f"Final price {pricing_result.final_price} exceeds customer "
                f"{customer.customer_id} credit limit {customer.credit_limit}",
            )

        reservation_result = self._reservation.reserve(resolved)
        if isinstance(reservation_result, ReservationFailure):
            return self._reject(order, reservation_result.reason)

        return self._confirm(order, pricing_result, reservation_result)

    def _confirm(
        self,
        order: Order,
        pricing_result: PricingResult,
        reservation_result: ReservationSuccess,
    ) -> OrderOutcome:
        outcome = OrderOutcome(
            order_id=order.order_id,
            status=OrderStatus.CONFIRMED,
            final_price=pricing_result.final_price,
            reservation_id=reservation_result.reservation_id,
            rejection_reason=None,
        )
        self._notification.notify(outcome)
        return outcome

    def _reject(self, order: Order, reason: str) -> OrderOutcome:
        outcome = OrderOutcome(
            order_id=order.order_id,
            status=OrderStatus.REJECTED,
            final_price=None,
            reservation_id=None,
            rejection_reason=reason,
        )
        self._notification.notify(outcome)
        return outcome


@dataclass(frozen=True)
class _Repositories:
    customers: InMemoryCustomerRepository
    products: InMemoryProductRepository
    inventory: InMemoryInventoryRepository
    promo_codes: InMemoryPromoCodeRepository


def _build_repositories(
    customer_seed: list[dict[str, object]],
    product_seed: list[dict[str, object]],
    inventory_seed: list[dict[str, object]],
    promo_seed: list[dict[str, object]],
) -> _Repositories:
    return _Repositories(
        customers=InMemoryCustomerRepository([build_customer(c) for c in customer_seed]),
        products=InMemoryProductRepository([build_product(p) for p in product_seed]),
        inventory=InMemoryInventoryRepository(
            [build_inventory_level(level) for level in inventory_seed]
        ),
        promo_codes=InMemoryPromoCodeRepository([build_promo_code(p) for p in promo_seed]),
    )


def build_pipeline(
    customer_seed: list[dict[str, object]],
    product_seed: list[dict[str, object]],
    inventory_seed: list[dict[str, object]],
    promo_seed: list[dict[str, object]],
    shipping_fee: str,
    clock: Clock | None = None,
) -> tuple[OrderPipeline, InMemoryNotificationSender]:
    """The composition root for the Classical exemplar."""
    repos = _build_repositories(customer_seed, product_seed, inventory_seed, promo_seed)
    effective_clock: Clock = clock or FixedClock(datetime(2026, 4, 10, 12, 0, 0))
    sender = InMemoryNotificationSender()
    pipeline = OrderPipeline(
        validation=ValidationService(repos.customers, repos.products, repos.inventory),
        pricing=PricingService(
            promo_codes=repos.promo_codes,
            shipping_fee=Decimal(shipping_fee),
            clock=effective_clock,
        ),
        reservation=ReservationService(repos.inventory, ReservationIdGenerator()),
        notification=NotificationService(sender),
    )
    return pipeline, sender
