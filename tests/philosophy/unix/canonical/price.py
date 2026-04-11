"""
price: the second stage of the Unix order pipeline.

    python -m tests.philosophy.unix.canonical.price --world world.json < in.jsonl > out.jsonl

Reads JSON-line orders from stdin. For orders with ``_status ==
"pending"``, computes subtotal, promo discount, shipping, final
price, and enforces the customer credit limit. Already-rejected
orders pass through unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from decimal import Decimal
from typing import Any


def _reject(order: dict[str, Any], reason: str) -> dict[str, Any]:
    return {**order, "_status": "rejected", "_rejection_reason": reason}


def price_one(
    order: dict[str, Any],
    world: dict[str, Any],
    now: datetime,
    shipping_fee: Decimal,
) -> dict[str, Any]:
    if order.get("_status") != "pending":
        return order

    resolved = order["_resolved"]
    subtotal = sum(
        (Decimal(item["unit_price"]) * item["quantity"] for item in resolved),
        start=Decimal(0),
    )

    discount = Decimal(0)
    code = order.get("promo_code")
    if code:
        promo = world["promo_codes"].get(code)
        if promo and datetime.fromisoformat(promo["expires_at"]) > now:
            discount = (subtotal * Decimal(promo["percent_off"]) / Decimal(100)).quantize(
                Decimal("0.01")
            )

    final_price = subtotal - discount + shipping_fee

    customer = order["_customer"]
    if final_price > Decimal(customer["credit_limit"]):
        return _reject(
            order,
            f"Final price {final_price} exceeds customer "
            f"{customer['customer_id']} credit limit {customer['credit_limit']}",
        )

    return {
        **order,
        "_subtotal": str(subtotal),
        "_discount": str(discount),
        "_final_price": str(final_price),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True, help="Path to world.json")
    parser.add_argument("--shipping-fee", required=True, help="Shipping fee as decimal string")
    parser.add_argument("--now", required=True, help="ISO datetime for promo expiry checks")
    args = parser.parse_args()

    with open(args.world, encoding="utf-8") as fh:
        world = json.load(fh)
    now = datetime.fromisoformat(args.now)
    shipping_fee = Decimal(args.shipping_fee)

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        order = json.loads(raw)
        print(json.dumps(price_one(order, world, now, shipping_fee)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
