"""Fixture for STAB-006: a Session() inside a yield-style dependency is exempt."""

from sqlalchemy.orm import Session


def get_session(engine):
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
