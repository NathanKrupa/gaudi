"""Fixture for PD-SCALE-001: a vectorized sum instead of row iteration."""

import pandas as pd


def total(df):
    return df["amount"].sum()
