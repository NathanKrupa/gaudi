"""Fixture for DJ-SEC-001: SECRET_KEY pulled from environment, not a literal."""

import os

import django  # noqa: F401  -- activates the django library gate

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = False
