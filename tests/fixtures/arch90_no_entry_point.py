"""Fixture: Script with CLI logic but no entry point."""

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    print(f"Hello, {args.name}")


if __name__ == "__main__":
    main()
