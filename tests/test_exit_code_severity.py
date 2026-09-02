# ABOUTME: --exit-code gates at the severity the caller selected, not at the error tier alone.
# ABOUTME: A skip still outranks a finding, so #257's exit 2 holds at every severity.

from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path

import pytest
from click.testing import CliRunner

from gaudi.cli import main

FIXTURES = Path(__file__).parent / "fixtures" / "exit_code_severity"
UNPARSABLE = Path(__file__).parent / "fixtures" / "skip_accounting" / "unparsable.py.txt"

SEVERITIES = ("error", "warn", "info")


def _scaffold(root: Path) -> None:
    """Write the files that satisfy every project-scope rule.

    Gaudi's project-scope rules (STRUCT-011, STRUCT-013, OPS-002..005) fire on
    the *directory*, not on any module in it, so a bare temp directory already
    carries one warn and four infos. A fixture that is meant to carry exactly
    one finding has to be a well-formed project first. The profile tests below
    pin that this list is still sufficient — if a new project-scope rule lands,
    they name it rather than letting it drift into the exit-code assertions.
    """
    (root / ".github").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname = "fixture"\nversion = "0"\n', encoding="utf-8"
    )
    (root / "requirements-lock.txt").write_text("click==8.1.7\n", encoding="utf-8")
    (root / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    (root / ".github" / "PULL_REQUEST_TEMPLATE.md").write_text("## Summary\n", encoding="utf-8")
    (root / ".github" / "CODEOWNERS").write_text("* @owner\n", encoding="utf-8")
    (root / "CONTRIBUTING.md").write_text("# Contributing\n", encoding="utf-8")


def _project(tmp_path: Path, fixture: str, *, with_skip: bool = False) -> Path:
    """Materialize a one-module project from a .py.txt fixture."""
    root = tmp_path / fixture
    root.mkdir()
    _scaffold(root)
    shutil.copyfile(FIXTURES / f"{fixture}.py.txt", root / f"{fixture}.py")
    if with_skip:
        shutil.copyfile(UNPARSABLE, root / "unparsable.py")
    return root


def _exit_code(project: Path, severity: str) -> int:
    result = CliRunner().invoke(
        main, ["check", str(project), "--severity", severity, "--exit-code"]
    )
    return result.exit_code


def _profile(project: Path) -> Counter[str]:
    result = CliRunner().invoke(
        main, ["check", str(project), "--severity", "info", "--format", "json"]
    )
    payload = json.loads(result.output)
    return Counter(finding["severity"] for finding in payload["findings"])


class TestFixtureProfiles:
    """Pins, not guards: the fixtures carry the finding profile the gate tests assume."""

    def test_the_clean_fixture_carries_no_finding_at_any_severity(self, tmp_path: Path):
        assert _profile(_project(tmp_path, "clean")) == Counter()

    def test_the_warn_fixture_carries_exactly_one_warn_finding(self, tmp_path: Path):
        assert _profile(_project(tmp_path, "warn_only")) == Counter({"warn": 1})

    def test_the_info_fixture_carries_exactly_one_info_finding(self, tmp_path: Path):
        assert _profile(_project(tmp_path, "info_only")) == Counter({"info": 1})

    def test_the_error_fixture_carries_exactly_one_error_finding(self, tmp_path: Path):
        assert _profile(_project(tmp_path, "error_only")) == Counter({"error": 1})


class TestGateHonorsTheThreshold:
    def test_a_warn_finding_fails_a_warn_gate(self, tmp_path: Path):
        """The defect: this exited 0 with a warning on the report."""
        assert _exit_code(_project(tmp_path, "warn_only"), "warn") == 1

    def test_a_warn_finding_fails_an_info_gate(self, tmp_path: Path):
        assert _exit_code(_project(tmp_path, "warn_only"), "info") == 1

    def test_a_warn_finding_passes_an_error_gate(self, tmp_path: Path):
        assert _exit_code(_project(tmp_path, "warn_only"), "error") == 0

    def test_an_info_finding_fails_an_info_gate(self, tmp_path: Path):
        assert _exit_code(_project(tmp_path, "info_only"), "info") == 1

    def test_an_info_finding_passes_a_warn_gate(self, tmp_path: Path):
        assert _exit_code(_project(tmp_path, "info_only"), "warn") == 0

    def test_an_info_finding_passes_an_error_gate(self, tmp_path: Path):
        assert _exit_code(_project(tmp_path, "info_only"), "error") == 0

    @pytest.mark.parametrize("severity", SEVERITIES)
    def test_an_error_finding_fails_every_gate(self, tmp_path: Path, severity: str):
        assert _exit_code(_project(tmp_path, "error_only"), severity) == 1

    @pytest.mark.parametrize("severity", SEVERITIES)
    def test_a_clean_project_passes_every_gate(self, tmp_path: Path, severity: str):
        assert _exit_code(_project(tmp_path, "clean"), severity) == 0

    def test_the_gate_is_silent_without_the_flag(self, tmp_path: Path):
        result = CliRunner().invoke(
            main, ["check", str(_project(tmp_path, "warn_only")), "--severity", "warn"]
        )
        assert result.exit_code == 0


class TestSkipStillOutranksFindings:
    """#257: exit 2 says the run was incomplete, and that outranks any finding."""

    @pytest.mark.parametrize("severity", SEVERITIES)
    @pytest.mark.parametrize("fixture", ("clean", "info_only", "warn_only", "error_only"))
    def test_an_unparsable_file_exits_two_at_every_severity(
        self, tmp_path: Path, fixture: str, severity: str
    ):
        project = _project(tmp_path, fixture, with_skip=True)
        assert _exit_code(project, severity) == 2
