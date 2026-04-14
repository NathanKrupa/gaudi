"""Fixture for DJ-SEC-001: SECRET_KEY with a test-placeholder value.

A settings file whose SECRET_KEY is clearly a test placeholder (contains
"test", "insecure", "dummy", etc.) should not trigger the rule.
"""

import django  # noqa: F401  -- activates the django library gate

SECRET_KEY = "test-secret-not-used-in-production"
