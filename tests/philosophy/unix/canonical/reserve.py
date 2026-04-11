"""
reserve: the third stage of the Unix order pipeline.

    python -m tests.philosophy.unix.canonical.reserve --world world.json < in.jsonl > out.jsonl

Reads JSON-line orders from stdin. For orders with ``_status ==
"pending"``, checks inventory availability and atomically reserves
stock. Mutates the ``world.json`` file in place (rewrite via
``os.replace`` for atomicity). Already-rejected orders pass through
unchanged.

Reservation IDs are monotonic; the counter lives in
``world["_reservation_counter"]`` and is incremented per confirmed
order so the file itself carries the state between invocations.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import tempfile
from typing import Any


def _reject(order: dict[str, Any], reason: str) -> dict[str, Any]:
    return {**order, "_status": "rejected", "_rejection_reason": reason}


def _insufficient_skus(resolved: list[dict[str, Any]], inventory: dict[str, Any]) -> list[str]:
    shortfalls: list[str] = []
    for item in resolved:
        level = inventory.get(item["sku"])
        available = (level["on_hand"] - level["reserved"]) if level else 0
        if available < item["quantity"]:
            shortfalls.append(item["sku"])
    return shortfalls


def reserve_one(
    order: dict[str, Any],
    world: dict[str, Any],
    reservation_counter: itertools.count,
) -> dict[str, Any]:
    if order.get("_status") != "pending":
        return order

    resolved = order["_resolved"]
    inventory = world["inventory"]

    insufficient = _insufficient_skus(resolved, inventory)
    if insufficient:
        return _reject(order, f"Insufficient inventory for: {', '.join(insufficient)}")

    for item in resolved:
        inventory[item["sku"]]["reserved"] += item["quantity"]

    return {
        **order,
        "_status": "confirmed",
        "_reservation_id": f"RES-{next(reservation_counter):06d}",
    }


def _atomic_write_json(path: str, data: dict[str, Any]) -> None:
    tmp_dir = os.path.dirname(os.path.abspath(path)) or "."
    with tempfile.NamedTemporaryFile(
        "w", delete=False, dir=tmp_dir, encoding="utf-8", suffix=".tmp"
    ) as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--world", required=True, help="Path to world.json (read+rewrite)")
    args = parser.parse_args()

    with open(args.world, encoding="utf-8") as fh:
        world = json.load(fh)

    counter_start = world.get("_reservation_counter", 1)
    counter = itertools.count(counter_start)

    out_orders: list[dict[str, Any]] = []
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        order = json.loads(raw)
        out_orders.append(reserve_one(order, world, counter))

    # Record how many reservation IDs this invocation consumed, so
    # subsequent runs start where this one left off.
    world["_reservation_counter"] = next(counter)
    _atomic_write_json(args.world, world)

    for order in out_orders:
        print(json.dumps(order))
    return 0


if __name__ == "__main__":
    sys.exit(main())
