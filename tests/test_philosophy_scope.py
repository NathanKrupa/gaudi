"""Unit tests for the Phase 1 philosophy-scope engine change.

These tests cover three discrete concerns and nothing else:

1. ``rule_applies_to_school`` obeys the one-predicate rule described in
   ``docs/philosophy/README.md``.
2. ``load_config`` parses ``[philosophy].school``, defaults it when
   absent, and raises on invalid schools.
3. Every currently-registered Python rule has a valid ``philosophy_scope``
   — a frozenset of known tokens. This is the guardrail that protects
   the eventual PR B tagging work from typos and stale tokens.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from gaudi.config import get_school, load_config
from gaudi.core import (
    DEFAULT_SCHOOL,
    UNIVERSAL_SCOPE,
    VALID_SCHOOLS,
    VALID_SCOPE_TOKENS,
    Rule,
    Severity,
)
from gaudi.pack import rule_applies_to_school
from gaudi.packs.python.rules import ALL_RULES


class _ScopedRule(Rule):
    code = "TEST-SCOPE-001"
    severity = Severity.INFO
    philosophy_scope = frozenset({"pragmatic", "unix"})

    def check(self, context):  # pragma: no cover - never invoked
        return []


class _UniversalRule(Rule):
    code = "TEST-SCOPE-002"
    severity = Severity.INFO

    def check(self, context):  # pragma: no cover
        return []


class TestRuleAppliesToSchool:
    def test_universal_rule_runs_under_every_school(self) -> None:
        rule = _UniversalRule()
        for school in VALID_SCHOOLS:
            assert rule_applies_to_school(rule, school), (
                f"universal rule should apply under {school!r}"
            )

    def test_scoped_rule_runs_only_under_its_declared_schools(self) -> None:
        rule = _ScopedRule()
        assert rule_applies_to_school(rule, "pragmatic")
        assert rule_applies_to_school(rule, "unix")
        assert not rule_applies_to_school(rule, "classical")
        assert not rule_applies_to_school(rule, "functional")

    def test_rule_with_universal_and_specific_scope_always_runs(self) -> None:
        rule = _UniversalRule()
        rule.philosophy_scope = frozenset({"universal", "classical"})
        # universal token short-circuits — this rule runs everywhere.
        for school in VALID_SCHOOLS:
            assert rule_applies_to_school(rule, school)


class TestConfigPhilosophy:
    def test_defaults_to_classical_when_file_missing(self, tmp_path: Path) -> None:
        config = load_config(tmp_path)
        assert get_school(config) == DEFAULT_SCHOOL == "classical"

    def test_respects_explicit_school(self, tmp_path: Path) -> None:
        (tmp_path / "gaudi.toml").write_text(
            '[philosophy]\nschool = "functional"\n',
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        assert get_school(config) == "functional"

    def test_preserves_existing_gaudi_table(self, tmp_path: Path) -> None:
        (tmp_path / "gaudi.toml").write_text(
            '[gaudi]\nexclude = ["build/"]\n\n[philosophy]\nschool = "unix"\n',
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        assert get_school(config) == "unix"
        assert config["exclude"] == ["build/"]

    def test_invalid_school_raises(self, tmp_path: Path) -> None:
        (tmp_path / "gaudi.toml").write_text(
            '[philosophy]\nschool = "gibberish"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="philosophy"):
            load_config(tmp_path)

    def test_defaults_when_philosophy_table_absent(self, tmp_path: Path) -> None:
        (tmp_path / "gaudi.toml").write_text(
            '[gaudi]\nexclude = ["build/"]\n',
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        assert get_school(config) == "classical"


class TestRegisteredRuleScopes:
    def test_every_python_rule_has_a_frozenset_scope(self) -> None:
        for rule_cls in ALL_RULES:
            scope = rule_cls.philosophy_scope
            assert isinstance(scope, frozenset), (
                f"{rule_cls.__name__} philosophy_scope must be a frozenset, "
                f"got {type(scope).__name__}"
            )
            assert scope, f"{rule_cls.__name__} philosophy_scope must not be empty"

    def test_every_python_rule_uses_known_tokens(self) -> None:
        for rule_cls in ALL_RULES:
            unknown = rule_cls.philosophy_scope - VALID_SCOPE_TOKENS
            assert not unknown, (
                f"{rule_cls.__name__} philosophy_scope contains unknown tokens: "
                f"{sorted(unknown)}. Valid tokens: {sorted(VALID_SCOPE_TOKENS)}"
            )

    def test_default_scope_on_base_rule_is_universal(self) -> None:
        assert Rule.philosophy_scope == UNIVERSAL_SCOPE
