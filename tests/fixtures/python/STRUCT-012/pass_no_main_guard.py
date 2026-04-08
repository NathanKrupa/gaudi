"""Fixture for STRUCT-012: argparse import but no `__main__` guard means it's not a script entry."""

import argparse


def build_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    return parser
