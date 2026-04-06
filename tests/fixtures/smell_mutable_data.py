"""Fixture: Mutable Data."""

_state = {"count": 0, "items": []}


def add_item(item):
    _state["items"].append(item)
    _state["count"] += 1


def reset():
    _state["items"].clear()
    _state["count"] = 0


def read_only_access():
    return len(_state["items"])
