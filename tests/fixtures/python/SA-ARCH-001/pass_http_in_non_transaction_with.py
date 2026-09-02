"""Fixture for SA-ARCH-001: a `with` block that is not a transaction.

The rule keys on the context manager, not on the mere presence of a `with`.
Most `with` blocks in a SQLAlchemy codebase open a file, a client or a lock;
firing on those would make the rule noise, and a noisy rule gets disabled
repo-wide -- which is exactly how STAB-011 and SVC-006 were lost.
"""

import httpx
import sqlalchemy  # noqa: F401  -- activates the sqlalchemy-gated rule


def snapshot(url: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(httpx.get(url).text)
