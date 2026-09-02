# ABOUTME: `gaudi count` -- the ratchet primitive: findings per rule code, machine-readable.
# ABOUTME: Its integer is only usable if an incomplete run cannot print like a complete one.

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from gaudi.cli import main
from gaudi.core import Category, Finding, Severity
from gaudi.services.ratchet import RATCHET_RULE_CODES, count_by_code

SKIP_FIXTURES = Path(__file__).parent / "fixtures" / "skip_accounting"

# A function long enough to trip SMELL-003 (>30 lines), in a project with a
# circular import pair to trip DEP-001. Both are in the debt set.
_LONG_FUNCTION = "def stretched():\n" + "".join(f"    x{i} = {i}\n" for i in range(40))


def _finding(code: str) -> Finding:
    return Finding(
        code=code,
        severity=Severity.WARN,
        category=Category.CODE_SMELL,
        message="m",
        recommendation="r",
    )


@pytest.fixture
def debt_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    root.mkdir()
    (root / "stretched.py").write_text(_LONG_FUNCTION, encoding="utf-8")
    (root / "tidy.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n", "utf-8")
    return root


class TestCountByCode:
    def test_counts_each_code(self):
        counts = count_by_code([_finding("A-1"), _finding("A-1"), _finding("B-2")])

        assert counts == {"A-1": 2, "B-2": 1}

    def test_requested_codes_are_always_present_even_at_zero(self):
        """A baseline whose keys move with the findings cannot be compared."""
        counts = count_by_code([_finding("A-1")], codes=["A-1", "B-2"])

        assert counts == {"A-1": 1, "B-2": 0}

    def test_codes_outside_the_request_are_excluded(self):
        counts = count_by_code([_finding("A-1"), _finding("Z-9")], codes=["A-1"])

        assert counts == {"A-1": 1}


class TestRatchetRuleSet:
    def test_the_debt_set_is_the_five_named_rules(self):
        assert set(RATCHET_RULE_CODES) == {
            "DEP-001",
            "DEP-004",
            "SMELL-003",
            "SMELL-007",
            "STAB-006",
        }

    @pytest.mark.parametrize("code", ["STRUCT-021", "CPLX-002", "SMELL-025"])
    def test_the_style_tier_is_not_debt(self, code: str):
        assert code not in RATCHET_RULE_CODES


class TestCountCli:
    def test_bare_count_prints_only_an_integer(self, debt_project: Path):
        result = CliRunner().invoke(main, ["count", str(debt_project)])

        assert result.exit_code == 0
        assert result.output.strip().isdigit()

    def test_code_filter_prints_only_that_code_s_integer(self, debt_project: Path):
        result = CliRunner().invoke(main, ["count", str(debt_project), "--code", "SMELL-003"])

        assert result.exit_code == 0
        assert result.output.strip() == "1"

    def test_a_code_that_never_fires_counts_zero(self, debt_project: Path):
        result = CliRunner().invoke(main, ["count", str(debt_project), "--code", "DEP-001"])

        assert result.output.strip() == "0"

    def test_json_emits_a_code_to_count_map(self, debt_project: Path):
        result = CliRunner().invoke(main, ["count", str(debt_project), "--format", "json"])

        payload = json.loads(result.output)
        assert payload["SMELL-003"] == 1

    def test_ratchet_counts_only_the_debt_set(self, debt_project: Path):
        """STRUCT-020 fires on this project; it must not reach the ratchet total."""
        everything = CliRunner().invoke(main, ["count", str(debt_project), "--format", "json"])
        ratchet = CliRunner().invoke(
            main, ["count", str(debt_project), "--ratchet", "--format", "json"]
        )

        all_codes = set(json.loads(everything.output))
        ratchet_codes = set(json.loads(ratchet.output))

        assert ratchet_codes == set(RATCHET_RULE_CODES)
        assert all_codes - ratchet_codes, "the project must carry non-debt findings to prove this"

    def test_ratchet_text_prints_the_debt_total(self, debt_project: Path):
        result = CliRunner().invoke(main, ["count", str(debt_project), "--ratchet"])

        assert result.exit_code == 0
        assert result.output.strip() == "1"

    def test_ratchet_and_code_together_are_refused(self, debt_project: Path):
        result = CliRunner().invoke(main, ["count", str(debt_project), "--ratchet", "--code", "X"])

        assert result.exit_code == 1
        assert "--code" in result.output


class TestCountCannotUndercountSilently:
    """An incomplete count is the false green a ratchet is most vulnerable to."""

    @pytest.fixture
    def skipping_project(self, tmp_path: Path) -> Path:
        root = tmp_path / "project"
        root.mkdir()
        shutil.copyfile(SKIP_FIXTURES / "clean.py.txt", root / "clean.py")
        shutil.copyfile(SKIP_FIXTURES / "unparsable.py.txt", root / "unparsable.py")
        return root

    def test_a_skip_makes_count_exit_two(self, skipping_project: Path):
        result = CliRunner().invoke(main, ["count", str(skipping_project)])

        assert result.exit_code == 2

    def test_a_complete_count_exits_zero(self, debt_project: Path):
        result = CliRunner().invoke(main, ["count", str(debt_project)])

        assert result.exit_code == 0

    def test_the_integer_still_reaches_stdout_when_files_were_skipped(self, skipping_project: Path):
        """The count is still the best available answer; the exit code says it is partial."""
        result = CliRunner().invoke(main, ["count", str(skipping_project)])

        assert result.stdout.strip().isdigit()

    def test_the_skip_reason_is_reported_off_stdout(self, skipping_project: Path):
        result = CliRunner().invoke(
            main, ["count", str(skipping_project)], catch_exceptions=False, standalone_mode=False
        )

        assert "unparsable.py" not in result.stdout
