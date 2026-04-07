"""Fixture for PD-ARCH-001: explicit inplace=False is fine (and equivalent to omitting it)."""

import pandas as pd


def clean(df):
    return df.dropna(inplace=False)
