"""Fixture for SMELL-002 boundary: bodies of exactly 15 AST nodes are compared."""


def shelf_code(item):
    if item.section:
        return item.code + item.section
    return item.code.upper()


def bin_code(entry):
    if entry.section:
        return entry.code + entry.section
    return entry.code.upper()
