"""Fixture for SMELL-002 boundary: bodies of 14 AST nodes are below the floor."""


def shelf_code(item):
    if item.section:
        return f"{item.code}{item.section}"
    return item.code


def bin_code(entry):
    if entry.section:
        return f"{entry.code}{entry.section}"
    return entry.code
