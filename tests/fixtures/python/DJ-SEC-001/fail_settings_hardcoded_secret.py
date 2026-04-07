"""Fixture for DJ-SEC-001: SECRET_KEY assigned to a string literal in settings."""

import django  # noqa: F401  -- activates the django library gate

SECRET_KEY = "django-insecure-very-bad-do-not-use"
DEBUG = False
