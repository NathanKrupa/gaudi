"""Fixture for LLM-ARCH-001: model name as a string literal in the API call."""

import anthropic

client = anthropic.Anthropic()


def ask(prompt):
    return client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
