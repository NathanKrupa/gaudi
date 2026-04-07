"""Fixture for LLM-ERR-001: a module that imports anthropic but makes no API call."""

import anthropic


def build_client():
    return anthropic.Anthropic()
