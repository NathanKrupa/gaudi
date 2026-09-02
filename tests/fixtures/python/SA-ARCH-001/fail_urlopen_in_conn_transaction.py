"""Fixture for SA-ARCH-001: urllib inside a psycopg-style `conn.transaction()`."""

import urllib.request

import sqlalchemy


def sync(conn: sqlalchemy.Connection, url: str) -> None:
    with conn.transaction():
        body = urllib.request.urlopen(url).read()
        conn.execute(sqlalchemy.text("INSERT INTO t VALUES (:b)"), {"b": body})
