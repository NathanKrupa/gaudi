"""Owning app uses its own model -- not a cross-boundary import."""

from apps.users.models import User


def register():
    return User.__name__
