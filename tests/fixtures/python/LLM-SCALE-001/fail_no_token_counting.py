"""Fixture for LLM-SCALE-001: API call without any token-counting safeguard."""

import os

import anthropic

MODEL = os.environ["ANTHROPIC_MODEL"]
client = anthropic.Anthropic()


def ask(prompt):
    try:
        return client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError:
        return None
