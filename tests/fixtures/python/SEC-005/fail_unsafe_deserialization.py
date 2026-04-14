"""Fixture for SEC-005: pickle.load/loads, yaml.load without SafeLoader, and marshal.load/loads."""

import pickle
import yaml
import marshal


def load_pickle_file(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def load_pickle_bytes(data):
    return pickle.loads(data)


def load_yaml(text):
    return yaml.load(text)


def load_marshal_file(path):
    with open(path, "rb") as f:
        return marshal.load(f)


def load_marshal_bytes(data):
    return marshal.loads(data)
