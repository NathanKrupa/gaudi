"""
Minimal Django settings for the Convention reference exemplar.

Under the canonical-task.md out-of-scope rules, this exemplar uses
the in-memory SQLite database. A real Django deployment would have
a full settings file per environment; this one is the minimum
needed for the test suite to load models, run migrations, and
exercise the admin.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

SECRET_KEY = "test-secret-not-used-in-production"  # noqa: S105  (test settings only)
DEBUG = False
ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "tests.philosophy.convention.canonical.apps.CanonicalConfig",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
STATIC_URL = "static/"
ROOT_URLCONF = "tests.philosophy.convention.canonical.urls"

SHIPPING_FEE = "5.00"
