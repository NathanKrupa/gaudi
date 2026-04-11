"""
Django app configuration for the Convention reference exemplar.

Under the Convention axiom, the AppConfig class is the blessed
entry point for per-app framework hooks. The exemplar uses the
stock config with an explicit ``label`` so multiple test runs
loading the same package under different installations do not
collide.
"""

from django.apps import AppConfig


class CanonicalConfig(AppConfig):
    name = "tests.philosophy.convention.canonical"
    label = "convention_canonical"
    default_auto_field = "django.db.models.BigAutoField"
