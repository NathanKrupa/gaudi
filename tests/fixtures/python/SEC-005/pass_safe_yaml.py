"""Fixture for SEC-005: yaml.load with an explicit SafeLoader."""

import yaml


def load_yaml(text):
    return yaml.load(text, Loader=yaml.SafeLoader)
