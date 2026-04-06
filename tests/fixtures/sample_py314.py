"""
Sample Python file with deliberate Python 3.14 compatibility issues.

Every import, pattern, and construct here is something that
breaks or triggers warnings in Python 3.14.
"""

# PY314-001: Removed AST node types
from ast import Num, Str, Bytes

# PY314-001: Removed asyncio child watchers
from asyncio import SafeChildWatcher, get_child_watcher

# PY314-001: Removed pkgutil functions
from pkgutil import find_loader, get_loader

# PY314-001: Removed sqlite3 version attrs
from sqlite3 import version as sqlite3_module_version

# PY314-002: Deprecated module
import pty

# PY314-002: Deprecated asyncio function
from asyncio import iscoroutinefunction


# PY314-003: Direct __annotations__ access (deferred in 3.14)
def inspect_annotations(cls):
    """Directly accessing __annotations__ is unreliable in 3.14."""
    return cls.__annotations__


# PY314-004: return in finally block
def risky_function():
    try:
        result = do_something()
    except Exception:
        handle_error()
    finally:
        return None  # Silently swallows exceptions — SyntaxWarning in 3.14


# PY314-004: break in finally block
def risky_loop():
    for i in range(10):
        try:
            process(i)
        finally:
            break  # Swallows exceptions


# PY314-005: NotImplemented in boolean context
def bad_comparison(self, other):
    result = self.__eq__(other)
    if NotImplemented:  # TypeError in 3.14!
        return False
    return result


# PY314-006: tarfile extraction without filter
import tarfile


def extract_archive(path):
    with tarfile.open(path) as tf:
        tf.extractall("/tmp/output")  # No filter= parameter — default changed in 3.14


# Helper stubs to make the file parseable
def do_something():
    pass


def handle_error():
    pass


def process(i):
    pass
