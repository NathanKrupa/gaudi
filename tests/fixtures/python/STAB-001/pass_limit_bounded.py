"""Fixture for STAB-001: .limit() bounds the result set.

The rule's own recommendation says "Add .limit()", so following its advice
must clear the finding. It did not -- ten sites across one estate repo carried
a permanent `# noqa: STAB-001` for queries that were correctly bounded (#245).
"""


def recent(session, Model):
    return session.query(Model).filter(Model.active).limit(50).all()
