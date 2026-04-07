"""Fixture for PD-ARCH-001: same operations done by reassignment."""

import pandas as pd


def clean(df):
    df = df.dropna()
    df = df.rename(columns={"a": "alpha"})
    return df
