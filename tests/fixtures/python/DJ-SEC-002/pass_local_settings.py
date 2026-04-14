"""Fixture for DJ-SEC-002: DEBUG=True in local/dev settings is expected."""

import django  # noqa: F401  -- activates the django library gate

DEBUG = True
