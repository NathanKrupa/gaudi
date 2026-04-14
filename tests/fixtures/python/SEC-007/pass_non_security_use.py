"""Passing fixture for SEC-007: random used for non-security purposes (simulation, tests)."""

import random


def roll_dice() -> int:
    return random.randint(1, 6)


def shuffle_deck(cards: list) -> list:
    random.shuffle(cards)
    return cards


def sample_rows(rows: list, k: int) -> list:
    return random.sample(rows, k)


def uniform_jitter() -> float:
    return random.uniform(0.0, 1.0)
