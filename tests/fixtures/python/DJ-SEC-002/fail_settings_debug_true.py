"""Fixture for DJ-SEC-002: DEBUG = True in a settings module."""

import os

import django  # noqa: F401  -- activates the django library gate

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = True
