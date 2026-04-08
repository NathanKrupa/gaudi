# ABOUTME: Aggregates all ops pack rules into a single ALL_RULES tuple.
# ABOUTME: Mirrors the python pack's rules/__init__.py registration pattern.
from gaudi.packs.ops.rules.dockerfile import DOCKERFILE_RULES

ALL_RULES = (*DOCKERFILE_RULES,)

__all__ = ("ALL_RULES",)
