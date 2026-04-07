"""Fixture for LLM-SCALE-001: API call alongside a count_tokens budget check."""

import os

import anthropic

MODEL = os.environ["ANTHROPIC_MODEL"]
client = anthropic.Anthropic()
TOKEN_BUDGET = 100_000


def ask(prompt):
    n = client.messages.count_tokens(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    ).input_tokens
    if n > TOKEN_BUDGET:
        raise ValueError("prompt exceeds token budget")
    try:
        return client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError:
        return None
