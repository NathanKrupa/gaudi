"""Fixture for ERR-007: lookups that fail loudly or default to a real value."""


def branch_city(record):
    return record["branch"]["city"]


def opening_hour(config):
    hours = config.get("hours")
    if hours is None:
        raise KeyError("hours")
    return hours.get("open", 9)


def tags(record):
    return record.get("tags", []) + record.get("labels", [])


def nested_default(record):
    return record.get("branch", {"city": "unknown"}).get("city")


def stage_label(report):
    return report.get("stages", {}).get("extracted", "-")


def open_count(store):
    # setdefault stores the empty dict, so later writes land in it.
    return store.setdefault("counts", {}).get("open", 0)
