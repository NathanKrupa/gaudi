"""Fixture for SMELL-008: only one function references the global."""

CONFIG = {"debug": False}


def get_config():
    return CONFIG


def init():
    return get_config()


def reload():
    return get_config().get("debug")


def is_debug():
    return get_config().get("debug", False)
