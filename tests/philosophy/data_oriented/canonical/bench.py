"""
Benchmark: per-order wall-clock cost of the SoA batch pipeline as a
function of batch size.

Run directly:

    conda run -n Oversteward python -m tests.philosophy.data_oriented.canonical.bench

The script synthesizes a world with 1,000 customers and 500 products
and processes batches of varying size (N = 1, 10, 100, 1_000,
10_000) through ``pipeline.process_orders_batch``. Times are
wall-clock over the processing call only; world construction is
excluded from the measurement.

Why this benchmark exists
-------------------------
The Data-Oriented axiom's catechism #1 is "measure first." A
performance claim without a measurement is a wish. This benchmark
exists so the exemplar ships with actual numbers attached to a real
machine, and so any future refactor of ``pipeline.py`` that hurts
throughput at any of the five measured batch sizes is caught by
rerunning this file.

What this benchmark does NOT claim
----------------------------------
It is **not** a "numpy beats pure Python" shootout. The exemplar
does more work than a stripped-down Python baseline (validates
customers, checks stock, computes discounts, enforces credit
limits, reserves inventory) so any comparison against a toy loop
that skips those stages would be noise pretending to be signal.
The honest reading is self-contained: here is what the batch
pipeline costs at this N on this hardware.

Measured numbers (Windows 11, Python 3.12, numpy 2.4, Intel 12th-
gen laptop CPU; values vary run-to-run by ~20%):

    N=    1:  ~0.0003 s  (≈ 280  us/order)  — numpy per-call overhead dominates
    N=   10:  ~0.0003 s  (≈  30  us/order)
    N=  100:  ~0.0006 s  (≈   6  us/order)
    N= 1000:  ~0.0040 s  (≈   4  us/order)
    N=10000:  ~0.0345 s  (≈ 3.5  us/order)  — per-order cost stabilizes

The per-order cost drops by almost two orders of magnitude between
N=1 and N=10_000. That is the empirical expression of the axiom's
claim that batching is the right granularity: numpy's entry cost
is paid once per call, not once per row, so the per-row cost
collapses as the batch grows. Below N≈100 the pipeline is paying
more than it earns; above N≈1000 it is in its intended regime.

For the acceptance-test suite (every test calls
``process_order``, i.e. a batch of 1) the exemplar runs in the
degenerate zone. That is deliberate: the acceptance tests exist
to verify correctness, and the rubric tests verify *shape*. The
benchmark exists to verify *cost*, separately, at a scale where
the shape is actually paying off.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from tests.philosophy.data_oriented.canonical.pipeline import process_orders_batch
from tests.philosophy.data_oriented.canonical.state import build_world

_NOW = datetime(2026, 4, 10, 12, 0, 0)
_SHIPPING_FEE = "5.00"


def _synth_world(n_customers: int, n_products: int) -> Any:
    customers = [
        {
            "customer_id": f"C{i:05d}",
            "name": f"Customer {i}",
            "email": f"c{i}@example.com",
            "standing": "good",
            "credit_limit": "100000.00",
        }
        for i in range(n_customers)
    ]
    products = [
        {
            "sku": f"SKU-{j:04d}",
            "name": f"Product {j}",
            "unit_price": f"{(j % 50) + 1}.00",
            "max_per_order": 100,
            "category": "widgets",
        }
        for j in range(n_products)
    ]
    inventory = [
        {"sku": f"SKU-{j:04d}", "on_hand": 10_000_000, "reserved": 0} for j in range(n_products)
    ]
    promo_codes = [
        {"code": "SAVE10", "percent_off": 10, "expires_at": "2099-12-31T23:59:59"},
    ]
    return build_world(customers, products, inventory, promo_codes)


def _synth_orders(n: int, n_customers: int, n_products: int) -> list[dict[str, Any]]:
    return [
        {
            "order_id": f"O{i:06d}",
            "customer_id": f"C{i % n_customers:05d}",
            "line_items": [
                {"sku": f"SKU-{(i * 3 + k) % n_products:04d}", "quantity": 1 + (k % 5)}
                for k in range(3)
            ],
            "promo_code": "SAVE10" if i % 7 == 0 else None,
            "shipping_address": "123 Main St",
        }
        for i in range(n)
    ]


def main() -> None:
    n_customers = 1_000
    n_products = 500
    sizes = (1, 10, 100, 1_000, 10_000)

    print("SoA batch pipeline — per-order wall-clock cost vs batch size")
    print(f"  world: {n_customers} customers, {n_products} products")
    print()
    for n in sizes:
        world = _synth_world(n_customers, n_products)
        orders = _synth_orders(n, n_customers, n_products)
        notifications: list[dict[str, Any]] = []
        # Warm once to avoid reporting first-call import cost as signal.
        if n == sizes[0]:
            _ = process_orders_batch(orders, world, _SHIPPING_FEE, _NOW, notifications)
            world = _synth_world(n_customers, n_products)
            notifications.clear()

        t0 = time.perf_counter()
        outcomes = process_orders_batch(orders, world, _SHIPPING_FEE, _NOW, notifications)
        elapsed = time.perf_counter() - t0
        confirmed = sum(1 for o in outcomes if o["status"] == "confirmed")
        per_order_us = (elapsed * 1e6 / n) if n else 0.0
        print(f"  N={n:>6}: {elapsed:.4f} s  ({per_order_us:7.2f} us/order)  confirmed={confirmed}")


if __name__ == "__main__":
    main()
