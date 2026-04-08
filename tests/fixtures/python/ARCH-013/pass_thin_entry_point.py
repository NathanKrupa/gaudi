"""Fixture for ARCH-013: a thin argparse entry point that delegates to a service."""

import argparse


def count_words(input_path, output_path, mode):
    return (input_path, output_path, mode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--mode")
    args = parser.parse_args()
    return count_words(args.input, args.output, args.mode)
