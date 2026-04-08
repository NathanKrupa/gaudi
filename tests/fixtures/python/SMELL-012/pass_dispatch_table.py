"""Fixture for SMELL-012: dispatch tables instead of repeated switches."""

LABELS = {"pending": "Pending", "paid": "Paid", "shipped": "Shipped"}
COLORS = {"pending": "yellow", "paid": "green", "shipped": "blue"}


def label(status):
    return LABELS.get(status, "?")


def color(status):
    return COLORS.get(status, "gray")
