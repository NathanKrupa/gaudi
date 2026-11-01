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


def section_label(report):
    return report.get("stages", {}).get("extracted", {}).get("label", "-")


def city_with_default(record):
    return record.get("branch", dict(city="unknown")).get("city")


def both_present(record):
    return (record.get("branch") and {}).get("city")


def first_present(record, fallback):
    return (record.get("branch") or fallback or {}).get("city")
