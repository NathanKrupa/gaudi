"""Fixture for ERR-007: chained .get() with an empty-dict default hides a missing key."""


def branch_city(record):
    return record.get("branch", {}).get("city")


def opening_hour(config):
    return config.get("hours", dict()).get("open", 9)


def manager_email(record):
    return (record.get("branch") or {}).get("manager", {}).get("email")


def keyword_default(payload):
    return payload.get("meta", default={}).get("source")


def branch_name(record):
    return record.get("branch", {}).get("name", "")
