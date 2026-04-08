"""Fixture for SMELL-008: CONFIG referenced in 4 functions."""

CONFIG = {"debug": False}


def init():
    return CONFIG


def reload():
    return CONFIG.get("debug")


def is_debug():
    return CONFIG.get("debug", False)


def reset():
    return CONFIG.clear()
