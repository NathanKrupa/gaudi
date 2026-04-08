"""Fixture for ARCH-013: an argparse entry point with >15 lines of body logic."""

import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input")
    parser.add_argument("--output")
    parser.add_argument("--mode")
    args = parser.parse_args()
    data = open(args.input).read()
    rows = data.splitlines()
    cleaned = [r.strip() for r in rows]
    filtered = [r for r in cleaned if r]
    counts = {}
    for r in filtered:
        counts[r] = counts.get(r, 0) + 1
    sorted_pairs = sorted(counts.items(), key=lambda kv: -kv[1])
    out = open(args.output, "w")
    for k, v in sorted_pairs:
        out.write(f"{k}\t{v}\n")
    out.close()
    return 0
