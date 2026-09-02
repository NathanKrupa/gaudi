"""Fixture for SA-ARCH-001: fetch first, then open the transaction.

This is the remedy the rule recommends, so it must not itself fire.
"""

import httpx
import sqlalchemy
from sqlalchemy.orm import Session


def enrich(session: Session, org_id: int) -> None:
    response = httpx.get(f"https://example.invalid/orgs/{org_id}")
    with session.begin():
        session.execute(sqlalchemy.text("UPDATE t SET v = :v"), {"v": response.text})
