"""Fixture for STRUCT-012: argparse + __main__ guard but no entry point in pyproject."""

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    args = parser.parse_args()
    return args.input


if __name__ == "__main__":
    main()
