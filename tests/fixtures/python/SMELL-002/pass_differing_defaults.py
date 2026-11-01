"""Fixture for SMELL-002: identical bodies behind different signatures are not copies."""


def fetch_page(client, path, limit=10):
    rows = client.get(path, params={"limit": limit})
    if not rows:
        return []
    return [row["id"] for row in rows if row.get("visible")]


def fetch_big_page(client, path, limit=500):
    rows = client.get(path, params={"limit": limit})
    if not rows:
        return []
    return [row["id"] for row in rows if row.get("visible")]
