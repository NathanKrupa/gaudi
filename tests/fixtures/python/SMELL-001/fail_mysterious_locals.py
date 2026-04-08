"""Fixture for SMELL-001: a function with 4 generic/single-letter locals."""


def crunch(items):
    data = []
    temp = 0
    val = None
    result = []
    for item in items:
        temp = item.value
        val = temp * 2
        data.append(val)
        result.append(data)
    return result
