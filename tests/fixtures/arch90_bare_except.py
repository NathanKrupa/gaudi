"""Fixture: Bare except and broad exception catching."""


def risky_operation():
    try:
        do_something()
    except:
        pass


def broad_catch():
    try:
        do_something()
    except Exception:
        pass


def good_catch():
    try:
        do_something()
    except ValueError:
        handle_error()
    except Exception:
        raise


def do_something():
    pass


def handle_error():
    pass
