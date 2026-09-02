"""Fixture for SA-ARCH-001: constructing a client is not making a request.

`httpx.Client()` is rooted on an HTTP module but performs no network I/O, so
it holds no lock open. The rule keys on the method as well as the receiver.
"""

import httpx
import sqlalchemy
from sqlalchemy.orm import Session


def prepare(session: Session, name: str) -> None:
    with session.begin():
        client = httpx.Client(timeout=5.0)
        session.execute(sqlalchemy.text("UPDATE org SET name = :n"), {"n": name})
        client.close()
