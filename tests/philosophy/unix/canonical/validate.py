"""
validate: the first stage of the Unix order pipeline.

    python -m tests.philosophy.unix.canonical.validate --world world.json < in.jsonl > out.jsonl

Reads one JSON order per stdin line, validates the customer and every
line item against the world file, and writes one JSON-line per output
order. Each output carries a ``_status`` of ``pending`` or
``rejected``; already-rejected orders (from upstream, if this stage
is composed differently) are passed through unchanged.

A pending order has ``_customer`` and ``_resolved`` fields attached
for downstream stages. A rejected order has ``_rejection_reason``.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _reject(order: dict[str, Any], reason: str) -> dict[str, Any]:
    return {**order, "_status": "rejected", "_rejection_reason": reason}


def validate_one(order: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    if order.get("_status") == "rejected":
        return order

    customers = world["customers"]
    products = world["products"]

    customer = customers.get(order["customer_id"])
    if customer is None:
        return _reject(order, f"Unknown customer {order['customer_id']}")
    if customer["standing"] != "good":
        return _reject(
            order,
            f"Customer {customer['customer_id']} standing is "
            f"{customer['standing']}; may not place orders",
        )

    resolved: list[dict[str, Any]] = []
    for line in order["line_items"]:
        product = products.get(line["sku"])
        if product is None:
            return _reject(order, f"Unknown product {line['sku']}")
        if line["quantity"] > product["max_per_order"]:
            return _reject(
                order,
                f"Line item {line['sku']} quantity {line['quantity']} "
                f"exceeds max_per_order {product['max_per_order']}",
            )
        resolved.append(
            {
                "sku": line["sku"],
                "quantity": line["quantity"],
                "unit_price": product["unit_price"],
                "max_per_order": product["max_per_order"],
            }
        )

    return {
        **order,
        "_status": "pending",
        "_customer": customer,
        "_resolved": resolved,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True, help="Path to world.json")
    args = parser.parse_args()

    with open(args.world, encoding="utf-8") as fh:
        world = json.load(fh)

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        order = json.loads(raw)
        print(json.dumps(validate_one(order, world)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
