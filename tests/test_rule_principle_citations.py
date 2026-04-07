"""Forcing function: every Rule subclass must cite its principles and source.

This test fails if any rule's class docstring lacks a well-formed `Principles:`
line and a `Source:` line. The Principles line must cite at least one and at
most three numbered principles from docs/principles.md (numbered 1-14).

Adding a new rule without citations is therefore impossible: the test will
break the build, and `docs/principles.md` becomes load-bearing on every
individual rule.
"""

from __future__ import annotations

import re

from gaudi.packs.python.rules import ALL_RULES

VALID_PRINCIPLE_NUMBERS = frozenset(range(1, 15))  # 1..14

PRINCIPLES_LINE_RE = re.compile(
    r"Principles:\s*((?:#\d+\s*\([^)]+\)(?:,\s*)?){1,3})\.",
    re.MULTILINE,
)
SOURCE_LINE_RE = re.compile(r"Source:\s*\S.*", re.MULTILINE)
PRINCIPLE_REF_RE = re.compile(r"#(\d+)")


def test_at_least_one_rule_discovered() -> None:
    """Sanity: ALL_RULES is non-empty so the assertions below aren't trivially green."""
    assert len(ALL_RULES) > 0, "ALL_RULES discovered no rules"


def test_every_rule_cites_principles() -> None:
    failures: list[str] = []
    for rule in ALL_RULES:
        cls = type(rule)
        doc = cls.__doc__ or ""
        match = PRINCIPLES_LINE_RE.search(doc)
        if not match:
            failures.append(
                f"{cls.__name__} ({rule.code}): missing or malformed `Principles:` line"
            )
            continue
        nums = [int(n) for n in PRINCIPLE_REF_RE.findall(match.group(1))]
        if not nums:
            failures.append(f"{cls.__name__} ({rule.code}): no principle numbers found in citation")
            continue
        if len(nums) > 3:
            failures.append(f"{cls.__name__} ({rule.code}): cites {len(nums)} principles (max 3)")
        invalid = [n for n in nums if n not in VALID_PRINCIPLE_NUMBERS]
        if invalid:
            failures.append(f"{cls.__name__} ({rule.code}): invalid principle numbers {invalid}")
    assert not failures, "Rules missing principle citations:\n  " + "\n  ".join(failures)


def test_every_rule_cites_source() -> None:
    failures: list[str] = []
    for rule in ALL_RULES:
        cls = type(rule)
        doc = cls.__doc__ or ""
        if not SOURCE_LINE_RE.search(doc):
            failures.append(f"{cls.__name__} ({rule.code}): missing `Source:` line")
    assert not failures, "Rules missing source citations:\n  " + "\n  ".join(failures)
