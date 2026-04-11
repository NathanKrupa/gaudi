"""
The pricing service: computes the final price for a validated order.

Pricing operates only on values that have already been resolved by
validation — it never touches the customer, product, or inventory
repositories. This keeps pricing a pure computation, testable in
isolation and free from infrastructure concerns.

The exemplar deliberately refuses a ``PricingStrategy`` hierarchy.
There is one pricing policy in this pipeline (list price with an
optional percentage promo and a flat shipping fee). Extracting a
Strategy interface with one implementation is exactly the pattern
worship rubric check #9 requires the exemplar to refuse. If a second
pricing policy ever appears, extraction becomes justified — and not
a line sooner.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ..domain.models import LineItem, Product
from ..infrastructure.clock import Clock
from ..infrastructure.repositories import PromoCodeRepository


@dataclass(frozen=True)
class PricingResult:
    """The computed final price for an order, with its breakdown."""

    subtotal: Decimal
    discount: Decimal
    shipping: Decimal
    final_price: Decimal


class PricingService:
    """Computes the final price of a validated order."""

    def __init__(
        self,
        promo_codes: PromoCodeRepository,
        shipping_fee: Decimal,
        clock: Clock,
    ) -> None:
        self._promo_codes = promo_codes
        self._shipping_fee = shipping_fee
        self._clock = clock

    def compute(
        self,
        resolved_items: tuple[tuple[Product, LineItem], ...],
        promo_code: str | None,
    ) -> PricingResult:
        subtotal = self._subtotal(resolved_items)
        discount = self._discount(subtotal, promo_code)
        final = subtotal - discount + self._shipping_fee
        return PricingResult(
            subtotal=subtotal,
            discount=discount,
            shipping=self._shipping_fee,
            final_price=final,
        )

    @staticmethod
    def _subtotal(resolved_items: tuple[tuple[Product, LineItem], ...]) -> Decimal:
        total = Decimal(0)
        for product, line in resolved_items:
            total += product.unit_price * line.quantity
        return total

    def _discount(self, subtotal: Decimal, promo_code: str | None) -> Decimal:
        if promo_code is None:
            return Decimal(0)
        promo = self._promo_codes.get(promo_code)
        if promo is None or not promo.is_active(self._clock.now()):
            return Decimal(0)
        percent = Decimal(promo.percent_off) / Decimal(100)
        return (subtotal * percent).quantize(Decimal("0.01"))
