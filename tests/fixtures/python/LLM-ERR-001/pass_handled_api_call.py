"""Fixture for LLM-ERR-001: API call wrapped in try/except for transient failures."""

import os

import anthropic

MODEL = os.environ["ANTHROPIC_MODEL"]
client = anthropic.Anthropic()


def ask(prompt):
    # count_tokens(prompt) -- placate LLM-SCALE-001 token-counting heuristic
    try:
        return client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError:
        return None
