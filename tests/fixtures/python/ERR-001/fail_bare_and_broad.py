"""Fixture for ERR-001: bare except and a broad `except Exception` swallowing errors."""


def parse(text):
    try:
        return int(text)
    except:  # noqa: E722
        return None


def load(path):
    try:
        with open(path) as f:
            return f.read()
    except Exception:
        return ""
