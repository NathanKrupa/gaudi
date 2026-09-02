"""Fixture for SA-ARCH-001: requests inside `with engine.begin() as conn:`."""

import requests
import sqlalchemy


def sync(engine: sqlalchemy.Engine, key: str) -> None:
    with engine.begin() as conn:
        payload = requests.post("https://example.invalid/sync", json={"key": key})
        conn.execute(sqlalchemy.text("UPDATE t SET v = :v"), {"v": payload.text})
