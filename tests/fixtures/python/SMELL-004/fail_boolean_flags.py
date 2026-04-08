"""Fixture for SMELL-004: 3 boolean defaults trips the alternate threshold."""


def render_page(title, *, debug=False, cache=True, secure=False):
    return (title, debug, cache, secure)
