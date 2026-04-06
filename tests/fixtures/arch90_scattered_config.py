"""Fixture: os.getenv() scattered across many functions."""

import os


def get_database_url():
    return os.getenv("DATABASE_URL")


def get_api_key():
    return os.getenv("API_KEY")


def get_secret():
    return os.environ.get("SECRET_KEY")


def get_debug():
    return os.getenv("DEBUG", "false") == "true"


def clean_function():
    return 42
