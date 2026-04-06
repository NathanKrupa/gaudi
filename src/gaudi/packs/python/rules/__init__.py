# ABOUTME: Python pack rules package, organized by category and library.
# ABOUTME: Aggregates all rule modules into a single ALL_RULES list.
"""Python pack rules, organized by category and library."""

from gaudi.packs.python.rules.architecture import ALL_RULES as ARCHITECTURE_RULES
from gaudi.packs.python.rules.py314 import PY314_RULES
from gaudi.packs.python.rules.django import DJANGO_LIB_RULES
from gaudi.packs.python.rules.fastapi import FASTAPI_RULES
from gaudi.packs.python.rules.sqlalchemy import SQLALCHEMY_RULES
from gaudi.packs.python.rules.flask import FLASK_RULES
from gaudi.packs.python.rules.celery import CELERY_RULES
from gaudi.packs.python.rules.pandas import PANDAS_RULES
from gaudi.packs.python.rules.requests_rules import REQUESTS_RULES
from gaudi.packs.python.rules.pydantic import PYDANTIC_RULES
from gaudi.packs.python.rules.pytest_rules import PYTEST_RULES
from gaudi.packs.python.rules.drf import DRF_RULES
from gaudi.packs.python.rules.smells import SMELL_RULES
from gaudi.packs.python.rules.arch90 import ARCH90_RULES
from gaudi.packs.python.rules.stability import STABILITY_RULES
from gaudi.packs.python.rules.services import SERVICE_RULES

ALL_RULES = (
    *ARCHITECTURE_RULES,
    *PY314_RULES,
    *DJANGO_LIB_RULES,
    *FASTAPI_RULES,
    *SQLALCHEMY_RULES,
    *FLASK_RULES,
    *CELERY_RULES,
    *PANDAS_RULES,
    *REQUESTS_RULES,
    *PYDANTIC_RULES,
    *PYTEST_RULES,
    *DRF_RULES,
    *SMELL_RULES,
    *ARCH90_RULES,
    *STABILITY_RULES,
    *SERVICE_RULES,
)
