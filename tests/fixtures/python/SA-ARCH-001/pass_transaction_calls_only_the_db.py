"""Fixture for SA-ARCH-001: ordinary method calls inside a transaction are fine.

`session.execute(...)`, `row.save()`, `conn.commit()` are attribute calls on
non-HTTP receivers. Only a call whose receiver root is a known HTTP client
module counts.
"""

import sqlalchemy
from sqlalchemy.orm import Session


def rename(session: Session, org_id: int, name: str) -> None:
    with session.begin():
        session.execute(sqlalchemy.text("UPDATE org SET name = :n"), {"n": name})
        session.get(org_id)
        session.send(name)
