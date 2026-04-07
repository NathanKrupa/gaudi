"""Fixture for PD-SCALE-001: a row-by-row loop using iterrows()."""

import pandas as pd


def total(df):
    out = 0
    for _, row in df.iterrows():
        out += row["amount"]
    return out
