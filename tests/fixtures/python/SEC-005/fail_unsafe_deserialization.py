"""Fixture for SEC-005: pickle.load/loads and yaml.load without a safe loader."""

import pickle
import yaml


def load_pickle_file(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def load_pickle_bytes(data):
    return pickle.loads(data)


def load_yaml(text):
    return yaml.load(text)
