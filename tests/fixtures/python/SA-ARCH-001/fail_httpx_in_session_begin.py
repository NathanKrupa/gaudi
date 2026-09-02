"""Fixture for SA-ARCH-001: an HTTP call inside a SQLAlchemy transaction block.

The canary for grantspider c58154b8 (four days CRASHED) and e236e1ad (357 rows
of paid model output lost). Both were network I/O holding a transaction open;
gaudi saw neither, because DJ-ARCH-004 only matched Django's
`transaction.atomic()` and the repo has none.
"""

import httpx
from sqlalchemy.orm import Session


def enrich(session: Session, org_id: int) -> None:
    with session.begin():
        row = session.get_org(org_id)
        response = httpx.get(f"https://example.invalid/orgs/{org_id}")
        row.payload = response.text
