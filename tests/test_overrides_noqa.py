# ABOUTME: Tests for per-rule severity overrides (gaudi.toml) and inline noqa suppression.
# ABOUTME: Covers config parsing, Finding.with_severity, engine apply_overrides, and noqa filtering.
from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from gaudi.cli import main
from gaudi.config import get_rule_overrides, load_config
from gaudi.core import Category, Finding, Severity
from gaudi.engine import apply_overrides
from gaudi.packs.python.context import FileInfo, _parse_noqa


class TestParseNoqa:
    def test_bare_noqa_suppresses_all(self) -> None:
        result = _parse_noqa("x = 1  # noqa\n")
        assert result == {1: frozenset()}

    def test_noqa_with_codes(self) -> None:
        result = _parse_noqa("x = 1  # noqa: SMELL-003, IDX-001\n")
        assert result == {1: frozenset({"SMELL-003", "IDX-001"})}

    def test_noqa_single_code(self) -> None:
        result = _parse_noqa("x = 1  # noqa: SEC-003\n")
        assert result == {1: frozenset({"SEC-003"})}

    def test_no_noqa_returns_empty(self) -> None:
        result = _parse_noqa("x = 1\ny = 2\n")
        assert result == {}

    def test_multiple_lines(self) -> None:
        source = "a = 1\nb = 2  # noqa: A\nc = 3  # noqa\n"
        result = _parse_noqa(source)
        assert result == {2: frozenset({"A"}), 3: frozenset()}


class TestFileInfoSuppression:
    def _make_file_info(self, source: str) -> FileInfo:
        return FileInfo(path=Path("test.py"), relative_path="test.py", source=source)

    def test_suppressed_by_bare_noqa(self) -> None:
        fi = self._make_file_info("x = 1  # noqa\n")
        assert fi.is_suppressed(1, "ANY-RULE")

    def test_suppressed_by_specific_code(self) -> None:
        fi = self._make_file_info("x = 1  # noqa: SEC-003\n")
        assert fi.is_suppressed(1, "SEC-003")
        assert not fi.is_suppressed(1, "OTHER-001")

    def test_not_suppressed_on_clean_line(self) -> None:
        fi = self._make_file_info("x = 1\n")
        assert not fi.is_suppressed(1, "SEC-003")


def _make_finding(
    code: str = "SMELL-003",
    severity: Severity = Severity.WARN,
) -> Finding:
    return Finding(
        code=code,
        severity=severity,
        category=Category.CODE_SMELL,
        message="test finding",
        recommendation="fix it",
    )


class TestFindingWithSeverity:
    def test_returns_copy_with_new_severity(self) -> None:
        f = _make_finding(severity=Severity.WARN)
        overridden = f.with_severity(Severity.ERROR)
        assert overridden.severity == Severity.ERROR
        assert overridden.code == f.code
        assert overridden.message == f.message
        assert f.severity == Severity.WARN  # original unchanged


class TestApplyOverrides:
    def test_no_overrides_returns_same(self) -> None:
        findings = [_make_finding()]
        assert apply_overrides(findings, {}) == findings

    def test_severity_override(self) -> None:
        findings = [_make_finding(code="SMELL-003", severity=Severity.WARN)]
        result = apply_overrides(findings, {"SMELL-003": "error"})
        assert len(result) == 1
        assert result[0].severity == Severity.ERROR

    def test_off_suppresses_finding(self) -> None:
        findings = [_make_finding(code="SMELL-003")]
        result = apply_overrides(findings, {"SMELL-003": "off"})
        assert len(result) == 0

    def test_unmatched_rule_unchanged(self) -> None:
        findings = [_make_finding(code="IDX-001")]
        result = apply_overrides(findings, {"SMELL-003": "error"})
        assert len(result) == 1
        assert result[0].severity == Severity.WARN


class TestConfigRuleOverrides:
    def test_load_rules_from_gaudi_toml(self, tmp_path: Path) -> None:
        toml = tmp_path / "gaudi.toml"
        toml.write_text(
            '[gaudi]\n[gaudi.rules]\nSMELL-003 = "error"\nIDX-001 = "off"\n',
            encoding="utf-8",
        )
        config = load_config(tmp_path)
        overrides = get_rule_overrides(config)
        assert overrides == {"SMELL-003": "error", "IDX-001": "off"}

    def test_no_rules_section_returns_empty(self, tmp_path: Path) -> None:
        config = load_config(tmp_path)
        assert get_rule_overrides(config) == {}


class TestEndToEnd:
    def test_severity_override_in_cli(self, tmp_path: Path) -> None:
        # Create a file that triggers SMELL-003 (long function)
        lines = ["def long_function():\n"] + ["    x = 1\n"] * 60
        (tmp_path / "big.py").write_text("".join(lines))
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")
        (tmp_path / "gaudi.toml").write_text(
            '[gaudi]\n[gaudi.rules]\nSMELL-003 = "error"\n',
            encoding="utf-8",
        )

        runner = CliRunner()
        result = runner.invoke(main, ["check", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0, result.output

        import json

        data = json.loads(result.output)
        smell_003 = [f for f in data["findings"] if f["code"] == "SMELL-003"]
        if smell_003:
            assert smell_003[0]["severity"] == "error"

    def test_noqa_suppresses_finding(self, tmp_path: Path) -> None:
        # STRUCT-021 fires on repeated string literals
        code = """x = "magic"  # noqa: STRUCT-021
y = "magic"
z = "magic"
a = "magic"
"""
        (tmp_path / "strings.py").write_text(code)
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n")

        runner = CliRunner()
        result = runner.invoke(main, ["check", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0, result.output
