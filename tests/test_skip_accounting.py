# ABOUTME: Skip accounting -- a file the parser cannot read is reported and counted.
# ABOUTME: "Could not look" must never print, serialize, or exit the same as "found nothing".

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from gaudi.cli import main
from gaudi.engine import Engine
from gaudi.packs.python.parser import parse_project

FIXTURES = Path(__file__).parent / "fixtures" / "skip_accounting"


def _project(tmp_path: Path, *fixtures: str) -> Path:
    """Materialize a project directory from the .py.txt fixtures."""
    root = tmp_path / "project"
    root.mkdir()
    for name in fixtures:
        shutil.copyfile(FIXTURES / f"{name}.py.txt", root / f"{name}.py")
    return root


@pytest.fixture
def clean_project(tmp_path: Path) -> Path:
    return _project(tmp_path, "clean")


@pytest.fixture
def skipping_project(tmp_path: Path) -> Path:
    return _project(tmp_path, "clean", "unparsable")


class TestParserRecordsSkips:
    def test_unparsable_file_is_recorded_with_a_reason(self, skipping_project: Path):
        context = parse_project(skipping_project)

        skipped = {s.file: s.reason for s in context.skipped}
        assert list(skipped) == ["unparsable.py"]
        assert "syntax" in skipped["unparsable.py"].lower()

    def test_parsable_project_records_no_skips(self, clean_project: Path):
        assert parse_project(clean_project).skipped == []

    @pytest.mark.skipif(
        sys.platform == "win32" or os.geteuid() == 0,
        reason="chmod-based unreadability is not enforced for root or on Windows",
    )
    def test_unreadable_file_is_recorded_with_a_reason(self, clean_project: Path):
        unreadable = clean_project / "locked.py"
        unreadable.write_text("x = 1\n", encoding="utf-8")
        unreadable.chmod(0o000)
        try:
            context = parse_project(clean_project)
        finally:
            unreadable.chmod(0o644)

        skipped = {s.file: s.reason for s in context.skipped}
        assert "locked.py" in skipped
        assert "unreadable" in skipped["locked.py"].lower()


class TestEngineSurfacesSkips:
    def test_check_result_carries_skips_alongside_findings(self, skipping_project: Path):
        engine = Engine()
        engine.discover_packs()

        result = engine.check_result(skipping_project)

        assert [s.file for s in result.skipped] == ["unparsable.py"]

    def test_check_result_on_a_clean_project_carries_no_skips(self, clean_project: Path):
        engine = Engine()
        engine.discover_packs()

        assert engine.check_result(clean_project).skipped == []


class TestCliReportsSkips:
    def test_text_output_names_the_skipped_file_and_reason(self, skipping_project: Path):
        result = CliRunner().invoke(main, ["check", str(skipping_project)])

        assert "1 file skipped" in result.output
        assert "unparsable.py" in result.output
        assert "syntax" in result.output.lower()

    def test_clean_run_does_not_mention_skips(self, clean_project: Path):
        result = CliRunner().invoke(main, ["check", str(clean_project)])

        assert "skipped" not in result.output.lower()

    def test_severity_filter_does_not_hide_skips(self, skipping_project: Path):
        result = CliRunner().invoke(main, ["check", str(skipping_project), "--severity", "error"])

        assert "1 file skipped" in result.output

    def test_json_output_lists_skipped_files(self, skipping_project: Path):
        result = CliRunner().invoke(main, ["check", str(skipping_project), "--format", "json"])

        payload = json.loads(result.output)
        assert [entry["file"] for entry in payload["skipped"]] == ["unparsable.py"]
        assert "syntax" in payload["skipped"][0]["reason"].lower()

    def test_json_output_on_a_clean_project_has_an_empty_skipped_list(self, clean_project: Path):
        result = CliRunner().invoke(main, ["check", str(clean_project), "--format", "json"])

        assert json.loads(result.output)["skipped"] == []

    def test_github_output_annotates_skipped_files(self, skipping_project: Path):
        result = CliRunner().invoke(main, ["check", str(skipping_project), "--format", "github"])

        assert "::warning file=unparsable.py" in result.output
        assert "gaudi could not parse" in result.output.lower()


class TestExitCode:
    def test_a_skip_turns_an_otherwise_clean_run_red(self, skipping_project: Path):
        """The negative fixture: one unparsable file, no findings, must exit 2."""
        result = CliRunner().invoke(main, ["check", str(skipping_project), "--exit-code"])

        assert result.exit_code == 2

    def test_a_clean_run_still_exits_zero(self, clean_project: Path):
        """The control for the skip case: no skip, no error, exit 0.

        Pinned at the error tier because the fixture directory is not a
        well-formed project -- it has no pyproject.toml or lock file, so the
        project-scope rules report one warning and four infos about the
        directory itself. Since #267 the gate is the threshold the caller
        selected, and those findings would fail an info-tier gate honestly.
        ``tests/test_exit_code_severity.py`` carries the project that is
        clean at every tier.
        """
        result = CliRunner().invoke(
            main, ["check", str(clean_project), "--severity", "error", "--exit-code"]
        )

        assert result.exit_code == 0

    def test_skips_are_silent_without_the_exit_code_flag(self, skipping_project: Path):
        result = CliRunner().invoke(main, ["check", str(skipping_project)])

        assert result.exit_code == 0
