"""
Data-Oriented state: Struct-of-Arrays world built once per batch.

The world holds every fact the hot path needs in column-oriented
numpy arrays. A row is not an object; it is an index that can be
used to read any column. The hot loop reads contiguous slices of
the columns it needs and ignores the rest, which is the whole
point of SoA.

Hot vs cold separation
----------------------
Hot columns are touched by the per-line and per-order inner loops:

- customer_credit_limit_cents     (int64)   credit check
- customer_standing               (uint8)   validate-customer stage
- product_unit_price_cents        (int64)   pricing stage
- product_max_per_order           (int32)   quantity validation
- inventory_on_hand               (int32)   shortage check and reservation
- inventory_reserved              (int32)   shortage check and reservation

Cold columns live in plain dicts and are only consulted on the
rejection-reason / notification path, which is off the hot loop:

- customer_cold[customer_id] -> {"name", "email"}
- product_cold[sku]          -> {"name", "category"}

Index maps (dict[str, int]) translate external identifiers into row
indices once, at world construction. The hot loop then addresses
the arrays by integer index and never touches a string hash.

Money
-----
Prices are stored as integer cents in int64 arrays. Float64 dollars
would give vectorization at the cost of rounding error on the
acceptance tests' exact-string expectations; int cents gives both
vectorization and exactness, which is the honest Data-Oriented
choice when the domain allows it.

Standing codes
--------------
Customer standing is encoded as uint8 (good=0, hold=1, banned=2)
so the validate-customer stage can do a single integer compare
against STANDING_GOOD instead of a string equality per row. String
names are kept in STANDING_NAMES for the rejection-reason path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import numpy as np

STANDING_GOOD: int = 0
STANDING_HOLD: int = 1
STANDING_BANNED: int = 2

STANDING_NAMES: dict[int, str] = {
    STANDING_GOOD: "good",
    STANDING_HOLD: "hold",
    STANDING_BANNED: "banned",
}

_STANDING_BY_NAME: dict[str, int] = {v: k for k, v in STANDING_NAMES.items()}


def _to_cents(amount: str) -> int:
    """Convert a decimal-string amount into integer cents.

    Done at world construction (cold path). The hot loop only sees
    int64 cents and never round-trips through Decimal.
    """
    return int(Decimal(amount) * 100)


@dataclass(frozen=True, slots=True)
class World:
    """Immutable SoA holder for one scenario's world state.

    Instances of ``World`` are frozen so the hot loop cannot
    accidentally rebind a column; mutation happens in-place on the
    two inventory arrays, which are still the same ndarrays the
    frozen reference points at.

    The ``slots=True`` is not a micro-optimization gesture — it is
    the minimum honest way to say "this record has a fixed set of
    columns, and any typo that invents a new one should be a
    TypeError at the call site, not a silent dict insert."
    """

    # --- identifier maps (cold; consulted once per order) -------------------
    customer_id_to_idx: dict[str, int]
    product_sku_to_idx: dict[str, int]
    product_idx_to_sku: list[str]
    customer_cold: dict[str, dict[str, Any]]
    product_cold: dict[str, dict[str, Any]]
    promo_codes: dict[str, dict[str, Any]]

    # --- hot columns (touched in the inner loops) ---------------------------
    customer_credit_limit_cents: np.ndarray
    customer_standing: np.ndarray
    product_unit_price_cents: np.ndarray
    product_max_per_order: np.ndarray
    inventory_on_hand: np.ndarray
    inventory_reserved: np.ndarray

    # --- per-call buffers (not part of the world proper) --------------------
    # Intentionally absent: batch-scratch arrays are allocated per
    # call in pipeline.process_orders_batch because their length is
    # bound to the batch size, which the world does not know.
    _marker: tuple[()] = field(default=())


def build_world(
    customers: list[dict[str, Any]],
    products: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    promo_codes: list[dict[str, Any]],
) -> World:
    """Construct a ``World`` from the shared seed-data row shape.

    Runs once per test (cold path). Allocates the six hot numpy
    columns, populates them by row index, and returns a frozen
    holder. Subsequent inventory mutation happens in-place on the
    ``inventory_on_hand`` / ``inventory_reserved`` arrays.
    """
    n_customers = len(customers)
    customer_id_to_idx: dict[str, int] = {}
    customer_credit_limit_cents = np.zeros(n_customers, dtype=np.int64)
    customer_standing = np.zeros(n_customers, dtype=np.uint8)
    customer_cold: dict[str, dict[str, Any]] = {}
    for i, row in enumerate(customers):
        cid = str(row["customer_id"])
        customer_id_to_idx[cid] = i
        customer_credit_limit_cents[i] = _to_cents(str(row["credit_limit"]))
        customer_standing[i] = _STANDING_BY_NAME[str(row["standing"])]
        customer_cold[cid] = {"name": row.get("name"), "email": row.get("email")}

    n_products = len(products)
    product_sku_to_idx: dict[str, int] = {}
    product_idx_to_sku: list[str] = [""] * n_products
    product_unit_price_cents = np.zeros(n_products, dtype=np.int64)
    product_max_per_order = np.zeros(n_products, dtype=np.int32)
    product_cold: dict[str, dict[str, Any]] = {}
    for j, row in enumerate(products):
        sku = str(row["sku"])
        product_sku_to_idx[sku] = j
        product_idx_to_sku[j] = sku
        product_unit_price_cents[j] = _to_cents(str(row["unit_price"]))
        product_max_per_order[j] = int(row["max_per_order"])  # type: ignore[arg-type]
        product_cold[sku] = {"name": row.get("name"), "category": row.get("category")}

    # Inventory rows are keyed by sku; align them with the product
    # index so the hot loop can use a shared sku_idx for both tables.
    inventory_on_hand = np.zeros(n_products, dtype=np.int32)
    inventory_reserved = np.zeros(n_products, dtype=np.int32)
    for row in inventory:
        sku = str(row["sku"])
        j = product_sku_to_idx[sku]
        inventory_on_hand[j] = int(row["on_hand"])  # type: ignore[arg-type]
        inventory_reserved[j] = int(row["reserved"])  # type: ignore[arg-type]

    promo_codes_map: dict[str, dict[str, Any]] = {str(p["code"]): dict(p) for p in promo_codes}

    return World(
        customer_id_to_idx=customer_id_to_idx,
        product_sku_to_idx=product_sku_to_idx,
        product_idx_to_sku=product_idx_to_sku,
        customer_cold=customer_cold,
        product_cold=product_cold,
        promo_codes=promo_codes_map,
        customer_credit_limit_cents=customer_credit_limit_cents,
        customer_standing=customer_standing,
        product_unit_price_cents=product_unit_price_cents,
        product_max_per_order=product_max_per_order,
        inventory_on_hand=inventory_on_hand,
        inventory_reserved=inventory_reserved,
    )


def cents_to_str(cents: int) -> str:
    """Format int cents as a two-decimal string (e.g. 2500 -> '25.00').

    Used at the rejection / notification boundary, never in the
    hot loop.
    """
    sign = "-" if cents < 0 else ""
    c = abs(int(cents))
    return f"{sign}{c // 100}.{c % 100:02d}"
