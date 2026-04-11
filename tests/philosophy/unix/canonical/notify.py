"""
notify: the fourth (terminal) stage of the Unix order pipeline.

    python -m tests.philosophy.unix.canonical.notify --log notifications.jsonl < in.jsonl > out.jsonl

Reads JSON-line orders from stdin. For every order (confirmed or
rejected), appends a notification record to the file named by
``--log``. Passes the order to stdout so callers can tee or
compose further downstream stages.

Under the Unix discipline, this is the "leaf" stage — its entire
job is to append to a file and echo the stream. It has no branching
business logic; it is a sink that happens to be composable.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def notification_record(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "order_id": order["order_id"],
        "status": order.get("_status", "unknown"),
        "final_price": order.get("_final_price"),
        "reservation_id": order.get("_reservation_id"),
        "rejection_reason": order.get("_rejection_reason"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log",
        required=True,
        help="Append JSON-line notification records to this file",
    )
    args = parser.parse_args()

    with open(args.log, "a", encoding="utf-8") as log_fh:
        for raw in sys.stdin:
            raw = raw.strip()
            if not raw:
                continue
            order = json.loads(raw)
            record = notification_record(order)
            log_fh.write(json.dumps(record) + "\n")
            print(json.dumps(order))
    return 0


if __name__ == "__main__":
    sys.exit(main())
