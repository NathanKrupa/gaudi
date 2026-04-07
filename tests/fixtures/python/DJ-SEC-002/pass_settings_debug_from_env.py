"""Fixture for DJ-SEC-002: DEBUG resolved from configuration, not a True literal."""

import os

import django  # noqa: F401  -- activates the django library gate

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG") == "1"
