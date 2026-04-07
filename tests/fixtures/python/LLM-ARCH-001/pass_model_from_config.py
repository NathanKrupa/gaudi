"""Fixture for LLM-ARCH-001: model name resolved from a configuration variable."""

import os

import anthropic

MODEL = os.environ["ANTHROPIC_MODEL"]
client = anthropic.Anthropic()


def ask(prompt):
    return client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
