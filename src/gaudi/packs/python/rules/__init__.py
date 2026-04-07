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
from gaudi.packs.python.rules.boto3 import BOTO3_RULES
from gaudi.packs.python.rules.drf import DRF_RULES
from gaudi.packs.python.rules.smells import SMELL_RULES
from gaudi.packs.python.rules.bloaters import BLOATER_RULES
from gaudi.packs.python.rules.dispensables import DISPENSABLE_RULES
from gaudi.packs.python.rules.couplers import COUPLER_RULES
from gaudi.packs.python.rules.oo_abusers import OO_ABUSER_RULES
from gaudi.packs.python.rules.change_preventers import CHANGE_PREVENTER_RULES
from gaudi.packs.python.rules.packaging import PACKAGING_RULES
from gaudi.packs.python.rules.layers import LAYERS_RULES
from gaudi.packs.python.rules.config_rules import CONFIG_RULES
from gaudi.packs.python.rules.types import TYPES_RULES
from gaudi.packs.python.rules.errors import ERRORS_RULES
from gaudi.packs.python.rules.logging_rules import LOGGING_RULES
from gaudi.packs.python.rules.ops import OPS_RULES
from gaudi.packs.python.rules.stability import STABILITY_RULES
from gaudi.packs.python.rules.services import SERVICE_RULES
from gaudi.packs.python.rules.anthropic_rules import ANTHROPIC_RULES
from gaudi.packs.python.rules.alembic import ALEMBIC_RULES
from gaudi.packs.python.rules.dependency import DEPENDENCY_RULES
from gaudi.packs.python.rules.security import SECURITY_RULES
from gaudi.packs.python.rules.complexity import COMPLEXITY_RULES

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
    *BOTO3_RULES,
    *DRF_RULES,
    *SMELL_RULES,
    *BLOATER_RULES,
    *DISPENSABLE_RULES,
    *COUPLER_RULES,
    *OO_ABUSER_RULES,
    *CHANGE_PREVENTER_RULES,
    *PACKAGING_RULES,
    *LAYERS_RULES,
    *CONFIG_RULES,
    *TYPES_RULES,
    *ERRORS_RULES,
    *LOGGING_RULES,
    *OPS_RULES,
    *STABILITY_RULES,
    *SERVICE_RULES,
    *ANTHROPIC_RULES,
    *ALEMBIC_RULES,
    *DEPENDENCY_RULES,
    *SECURITY_RULES,
    *COMPLEXITY_RULES,
)
