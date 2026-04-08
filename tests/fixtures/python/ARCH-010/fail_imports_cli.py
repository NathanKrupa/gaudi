"""Fixture for ARCH-010: an inner file importing from cli/views/scripts."""

from cli.main import run
from views.dashboard import render
import scripts.bootstrap


def use():
    return (run, render, scripts.bootstrap)
