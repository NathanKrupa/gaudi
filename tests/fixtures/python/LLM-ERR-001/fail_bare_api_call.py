"""Fixture for LLM-ERR-001: Anthropic API call with no try/except around it."""

import os

import anthropic

MODEL = os.environ["ANTHROPIC_MODEL"]
client = anthropic.Anthropic()


def ask(prompt):
    # count_tokens(prompt) -- placate LLM-SCALE-001 token-counting heuristic
    return client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
