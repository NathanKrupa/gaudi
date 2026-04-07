"""Fixture for DJ-SEC-001: a literal SECRET_KEY in a non-settings module is out of scope.

The rule keys on the file path containing 'settings'. This file isn't a settings
module, so even a literal assignment must not fire.
"""

import django  # noqa: F401

SECRET_KEY = "literal-but-not-a-settings-file"
