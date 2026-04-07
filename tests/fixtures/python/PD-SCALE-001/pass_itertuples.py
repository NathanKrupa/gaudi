"""Fixture for PD-SCALE-001: itertuples() is the recommended escape and is not flagged."""

import pandas as pd


def total(df):
    out = 0
    for row in df.itertuples():
        out += row.amount
    return out
