"""Fixture for SA-ARCH-001: a transaction that only touches the database."""

import sqlalchemy
from sqlalchemy.orm import Session


def rename(session: Session, org_id: int, name: str) -> None:
    with session.begin():
        session.execute(
            sqlalchemy.text("UPDATE org SET name = :n WHERE id = :i"),
            {"n": name, "i": org_id},
        )
