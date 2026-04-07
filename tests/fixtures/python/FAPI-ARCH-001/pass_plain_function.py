"""Fixture for FAPI-ARCH-001: a plain function in a fastapi-aware module is out of scope."""

from fastapi import FastAPI

app = FastAPI()


def compute_total(items):
    return sum(items)


_ = app
