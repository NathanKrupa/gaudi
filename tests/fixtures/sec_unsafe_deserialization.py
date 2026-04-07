# Fixture for SEC-005 UnsafeDeserialization.
import json
import pickle

import yaml


def load_pickle_file(path):
    # POSITIVE: pickle.load
    with open(path, "rb") as f:
        return pickle.load(f)


def load_pickle_bytes(data):
    # POSITIVE: pickle.loads
    return pickle.loads(data)


def load_yaml_unsafe(stream):
    # POSITIVE: yaml.load without SafeLoader
    return yaml.load(stream)


def load_yaml_safe(stream):
    # NEGATIVE: yaml.load with SafeLoader
    return yaml.load(stream, Loader=yaml.SafeLoader)


def load_yaml_safe_helper(stream):
    # NEGATIVE: yaml.safe_load
    return yaml.safe_load(stream)


def load_json(data):
    # NEGATIVE: json.loads is fine
    return json.loads(data)
