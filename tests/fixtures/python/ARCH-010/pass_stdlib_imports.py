"""Fixture for ARCH-010: stdlib imports don't trip the rule."""

import os
import sys
from pathlib import Path


def use():
    return (os, sys, Path)
