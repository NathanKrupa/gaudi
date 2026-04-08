"""Fixture for STAB-006: open() and Session() outside `with` blocks leak handles."""

from sqlalchemy.orm import Session


def read_config():
    f = open("config.txt")
    data = f.read()
    f.close()
    return data


def write_log(msg):
    f = open("log.txt", "a")
    f.write(msg)
    f.close()


def get_user(engine, user_id):
    session = Session(engine)
    return session.get(object, user_id)
