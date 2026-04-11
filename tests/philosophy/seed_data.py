"""
Shared seed data for every philosophy-school reference implementation
of the canonical order-processing task.

This module contains only plain Python data (lists of dicts, strings,
and timestamps). It deliberately imports nothing from any school's
implementation so that each school can parse the seed into its own
domain types without contamination. Every reference implementation
is required to run against this exact seed data unchanged — divergence
in test output must be attributable to architectural differences,
not to setup differences.

The seed covers every acceptance-criterion case listed in
``docs/philosophy/canonical-task.md``.
"""

from __future__ import annotations

SHIPPING_FEE = "5.00"


CUSTOMERS: list[dict[str, object]] = [
    {
        "customer_id": "C001",
        "name": "Alice Wellfunded",
        "email": "alice@example.com",
        "standing": "good",
        "credit_limit": "1000.00",
    },
    {
        "customer_id": "C002",
        "name": "Bob Tight",
        "email": "bob@example.com",
        "standing": "good",
        "credit_limit": "50.00",
    },
    {
        "customer_id": "C003",
        "name": "Carol Onhold",
        "email": "carol@example.com",
        "standing": "hold",
        "credit_limit": "500.00",
    },
    {
        "customer_id": "C004",
        "name": "Dave Banned",
        "email": "dave@example.com",
        "standing": "banned",
        "credit_limit": "1000.00",
    },
]


PRODUCTS: list[dict[str, object]] = [
    {
        "sku": "WIDGET-01",
        "name": "Standard Widget",
        "unit_price": "10.00",
        "max_per_order": 20,
        "category": "widgets",
    },
    {
        "sku": "WIDGET-02",
        "name": "Premium Widget",
        "unit_price": "25.00",
        "max_per_order": 5,
        "category": "widgets",
    },
    {
        "sku": "GADGET-01",
        "name": "Basic Gadget",
        "unit_price": "5.00",
        "max_per_order": 50,
        "category": "gadgets",
    },
    {
        "sku": "GADGET-02",
        "name": "Advanced Gadget",
        "unit_price": "15.00",
        "max_per_order": 10,
        "category": "gadgets",
    },
    {
        "sku": "SCARCE-01",
        "name": "Low Stock Item",
        "unit_price": "40.00",
        "max_per_order": 5,
        "category": "widgets",
    },
    {
        "sku": "EMPTY-01",
        "name": "Out of Stock Item",
        "unit_price": "20.00",
        "max_per_order": 10,
        "category": "gadgets",
    },
]


INVENTORY: list[dict[str, object]] = [
    {"sku": "WIDGET-01", "on_hand": 100, "reserved": 0},
    {"sku": "WIDGET-02", "on_hand": 50, "reserved": 0},
    {"sku": "GADGET-01", "on_hand": 200, "reserved": 0},
    {"sku": "GADGET-02", "on_hand": 30, "reserved": 0},
    {"sku": "SCARCE-01", "on_hand": 3, "reserved": 0},
    {"sku": "EMPTY-01", "on_hand": 0, "reserved": 0},
]


PROMO_CODES: list[dict[str, object]] = [
    {
        "code": "SAVE10",
        "percent_off": 10,
        "expires_at": "2099-12-31T23:59:59",
    },
    {
        "code": "OLDDEAL",
        "percent_off": 20,
        "expires_at": "2020-01-01T00:00:00",
    },
]


# Each test case states its name, the order input, the expected status,
# and (for confirmed orders) the expected final price. Rejection reasons
# are checked by substring so every school can phrase them idiomatically.
TEST_ORDERS: list[dict[str, object]] = [
    {
        "name": "happy_path_confirmed",
        "order": {
            "order_id": "O001",
            "customer_id": "C001",
            "line_items": [{"sku": "WIDGET-01", "quantity": 2}],
            "promo_code": None,
            "shipping_address": "123 Main St",
        },
        "expected_status": "confirmed",
        "expected_final_price": "25.00",  # 2 * 10.00 + 5.00 shipping
    },
    {
        "name": "valid_promo_discounts_price",
        "order": {
            "order_id": "O002",
            "customer_id": "C001",
            "line_items": [{"sku": "WIDGET-02", "quantity": 2}],
            "promo_code": "SAVE10",
            "shipping_address": "123 Main St",
        },
        "expected_status": "confirmed",
        # (2 * 25.00) * 0.90 + 5.00 shipping = 45.00 + 5.00 = 50.00
        "expected_final_price": "50.00",
    },
    {
        "name": "expired_promo_silently_ignored",
        "order": {
            "order_id": "O003",
            "customer_id": "C001",
            "line_items": [{"sku": "WIDGET-01", "quantity": 3}],
            "promo_code": "OLDDEAL",
            "shipping_address": "123 Main St",
        },
        "expected_status": "confirmed",
        # expired promo -> ignored, full price applies: 3 * 10.00 + 5.00 = 35.00
        "expected_final_price": "35.00",
    },
    {
        "name": "customer_on_hold_rejected",
        "order": {
            "order_id": "O004",
            "customer_id": "C003",
            "line_items": [{"sku": "WIDGET-01", "quantity": 1}],
            "promo_code": None,
            "shipping_address": "456 Oak St",
        },
        "expected_status": "rejected",
        "expected_reason_contains": "standing",
    },
    {
        "name": "customer_banned_rejected",
        "order": {
            "order_id": "O005",
            "customer_id": "C004",
            "line_items": [{"sku": "WIDGET-01", "quantity": 1}],
            "promo_code": None,
            "shipping_address": "789 Pine St",
        },
        "expected_status": "rejected",
        "expected_reason_contains": "standing",
    },
    {
        "name": "over_quantity_rejected",
        "order": {
            "order_id": "O006",
            "customer_id": "C001",
            "line_items": [{"sku": "WIDGET-02", "quantity": 10}],  # max_per_order = 5
            "promo_code": None,
            "shipping_address": "123 Main St",
        },
        "expected_status": "rejected",
        "expected_reason_contains": "WIDGET-02",
    },
    {
        "name": "exceeds_credit_limit_rejected",
        "order": {
            "order_id": "O007",
            "customer_id": "C002",  # credit limit = 50.00
            "line_items": [{"sku": "WIDGET-02", "quantity": 5}],  # 5 * 25 = 125 + 5 = 130
            "promo_code": None,
            "shipping_address": "555 Elm St",
        },
        "expected_status": "rejected",
        "expected_reason_contains": "credit",
    },
    {
        "name": "out_of_stock_rejected",
        "order": {
            "order_id": "O008",
            "customer_id": "C001",
            "line_items": [{"sku": "EMPTY-01", "quantity": 1}],
            "promo_code": None,
            "shipping_address": "123 Main St",
        },
        "expected_status": "rejected",
        "expected_reason_contains": "EMPTY-01",
    },
    {
        "name": "multiple_unfillable_lines_all_named",
        "order": {
            "order_id": "O009",
            "customer_id": "C001",
            "line_items": [
                {"sku": "WIDGET-01", "quantity": 2},
                {"sku": "SCARCE-01", "quantity": 5},  # only 3 in stock
                {"sku": "EMPTY-01", "quantity": 1},  # 0 in stock
            ],
            "promo_code": None,
            "shipping_address": "123 Main St",
        },
        "expected_status": "rejected",
        # Both insufficient items must be named, not just the first.
        "expected_reason_contains_all": ["SCARCE-01", "EMPTY-01"],
    },
    {
        "name": "unknown_product_rejected",
        "order": {
            "order_id": "O010",
            "customer_id": "C001",
            "line_items": [{"sku": "NOSUCH-99", "quantity": 1}],
            "promo_code": None,
            "shipping_address": "123 Main St",
        },
        "expected_status": "rejected",
        "expected_reason_contains": "NOSUCH-99",
    },
]
