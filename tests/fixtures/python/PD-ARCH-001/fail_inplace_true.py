"""Fixture for PD-ARCH-001: pandas calls with inplace=True."""

import pandas as pd


def clean(df):
    df.dropna(inplace=True)
    df.rename(columns={"a": "alpha"}, inplace=True)
    return df
