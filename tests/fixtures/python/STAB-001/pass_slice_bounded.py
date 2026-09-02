"""Fixture for STAB-001: Python slicing bounds an ORM result set.

`Model.objects.all()[:20]` compiles to LIMIT 20 in Django; the result set is
bounded before it reaches memory.
"""


def recent(Model):
    return Model.objects.all()[:20]
