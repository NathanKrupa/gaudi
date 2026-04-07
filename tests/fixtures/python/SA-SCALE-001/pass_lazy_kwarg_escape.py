"""Fixture for SA-SCALE-001: a relationship() call escaped by the lazy kwarg.

This fixture imports sqlalchemy so the rule actually activates, then proves
that supplying `lazy=` is a sufficient escape regardless of which symbol
named `relationship` is being called.
"""

import sqlalchemy  # noqa: F401 -- activates the rule


def relationship(target, **kwargs):
    return (target, kwargs)


x = relationship("Item", lazy="selectin")
