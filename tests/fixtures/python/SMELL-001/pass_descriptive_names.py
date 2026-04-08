"""Fixture for SMELL-001: descriptive names reveal intent."""


def crunch(items):
    doubled_values = []
    for item in items:
        doubled = item.value * 2
        doubled_values.append(doubled)
    return doubled_values
