"""Fixture for ERR-005: all raised exceptions share a common project base class."""


class ServiceError(Exception):
    pass


class NotFoundError(ServiceError):
    pass


class ConflictError(ServiceError):
    pass


class TimeoutError_(ServiceError):
    pass


class ValidationError(ServiceError):
    pass


def a():
    raise NotFoundError("missing")


def b():
    raise ConflictError("dup")


def c():
    raise TimeoutError_("slow")


def d():
    raise ValidationError("bad")
