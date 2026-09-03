# ABOUTME: A path no installed pack applies to was never examined, and must not read as clean.
# ABOUTME: "Examined everything and found nothing" and "examined nothing" must never print alike.

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from gaudi.cli import main
from gaudi.engine import Engine

NOTHING_EXAMINED = "No language pack applies here, so nothing was examined."


@pytest.fixture
def unhandled_project(tmp_path: Path) -> Path:
    """A directory holding nothing any installed pack claims."""
    root = tmp_path / "prose"
    root.mkdir()
    (root / "notes.txt").write_text("just some notes\n", encoding="utf-8")
    (root / "chapter.md").write_text("# Chapter one\n", encoding="utf-8")
    return root


def _scaffold(root: Path) -> None:
    """Write the files that satisfy every project-scope rule.

    Gaudi's project-scope rules fire on the *directory*, so a bare temp
    directory carries six findings before any module is copied in. A control
    that is meant to be clean has to be well-formed first. Same list as
    ``tests/test_exit_code_severity.py``, which pins that it is sufficient.
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


@pytest.fixture
def handled_project(tmp_path: Path) -> Path:
    """The control: a well-formed directory the Python pack claims."""
    root = tmp_path / "code"
    root.mkdir()
    _scaffold(root)
    (root / "clean.py").write_text(
        '"""A module with nothing to report."""\n\n\ndef add(a: int, b: int) -> int:\n'
        "    return a + b\n",
        encoding="utf-8",
    )
    return root


class TestTheEngineRecordsThatNothingWasExamined:
    def test_a_path_no_pack_applies_to_is_marked_unexamined(self, unhandled_project: Path):
        engine = Engine()
        engine.discover_packs()

        result = engine.check_result(unhandled_project)

        assert result.examined is False
        assert result.findings == []

    def test_a_path_a_pack_applies_to_is_marked_examined(self, handled_project: Path):
        engine = Engine()
        engine.discover_packs()

        assert engine.check_result(handled_project).examined is True


class TestCheckSaysNothingWasExamined:
    def test_the_text_renderer_does_not_call_it_structurally_sound(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["check", str(unhandled_project)])

        assert "Structurally sound" not in result.output

    def test_the_text_renderer_says_nothing_was_examined(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["check", str(unhandled_project)])

        assert NOTHING_EXAMINED in result.output

    def test_the_text_renderer_says_what_gaudi_does_handle(self, unhandled_project: Path):
        """A reader told nothing applied needs to know what would have."""
        result = CliRunner().invoke(main, ["check", str(unhandled_project)])

        assert "matched an installed pack" in result.output
        assert "python" in result.output
        assert ".py" in result.output

    def test_it_exits_two_under_the_exit_code_flag(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["check", str(unhandled_project), "--exit-code"])

        assert result.exit_code == 2

    @pytest.mark.parametrize("severity", ["error", "warn", "info"])
    def test_it_exits_two_at_every_severity(self, unhandled_project: Path, severity: str):
        result = CliRunner().invoke(
            main, ["check", str(unhandled_project), "--severity", severity, "--exit-code"]
        )

        assert result.exit_code == 2

    def test_the_json_document_records_it(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["check", str(unhandled_project), "--format", "json"])

        payload = json.loads(result.stdout)
        assert payload["examined"] is False
        assert payload["summary"] == NOTHING_EXAMINED

    def test_the_github_output_annotates_it(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["check", str(unhandled_project), "--format", "github"])

        assert "::error title=Nothing examined::" in result.stdout


class TestCountAndReportSayItToo:
    def test_count_exits_two(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["count", str(unhandled_project)])

        assert result.exit_code == 2

    def test_count_keeps_the_integer_on_stdout(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["count", str(unhandled_project)])

        assert result.stdout.strip().isdigit()

    def test_count_says_what_happened_on_stderr(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["count", str(unhandled_project)])

        assert "nothing was examined" in result.stderr.lower()
        assert "undercount" in result.stderr

    def test_report_names_it_in_the_incomplete_run_block(self, unhandled_project: Path):
        """Assert on the *bullet*, not on the verdict sentence.

        The verdict line also contains "No language pack applies", so a looser
        assertion is satisfied with the block's only bullet deleted -- an
        Incomplete run heading over an empty list.
        """
        result = CliRunner().invoke(main, ["report", str(unhandled_project)])

        assert "## Incomplete run" in result.stdout
        assert "- **No language pack applies to this path**" in result.stdout
        assert "Structurally sound" not in result.stdout

    def test_report_exits_two(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["report", str(unhandled_project)])

        assert result.exit_code == 2


class TestAnExaminedPathIsUnaffected:
    """The controls: every claim above must be false on a path a pack did examine."""

    def test_the_text_renderer_still_says_structurally_sound(self, handled_project: Path):
        result = CliRunner().invoke(main, ["check", str(handled_project)])

        assert "No architectural issues found. Structurally sound." in result.output
        assert NOTHING_EXAMINED not in result.output

    def test_it_still_exits_zero(self, handled_project: Path):
        result = CliRunner().invoke(main, ["check", str(handled_project), "--exit-code"])

        assert result.exit_code == 0

    def test_the_json_document_records_the_run_as_examined(self, handled_project: Path):
        result = CliRunner().invoke(main, ["check", str(handled_project), "--format", "json"])

        payload = json.loads(result.stdout)
        assert payload["examined"] is True
        assert payload["summary"] == "No architectural issues found. Structurally sound."

    def test_the_github_output_says_nothing(self, handled_project: Path):
        result = CliRunner().invoke(main, ["check", str(handled_project), "--format", "github"])

        assert "Nothing examined" not in result.stdout

    def test_count_still_exits_zero_and_says_nothing_on_stderr(self, handled_project: Path):
        result = CliRunner().invoke(main, ["count", str(handled_project)])

        assert result.exit_code == 0
        assert result.stderr == ""

    def test_report_still_exits_zero(self, handled_project: Path):
        result = CliRunner().invoke(main, ["report", str(handled_project)])

        assert result.exit_code == 0
        assert "Incomplete run" not in result.stdout


@pytest.fixture
def dockerfile_project(tmp_path: Path) -> Path:
    """A directory the ops pack claims and the Python pack does not."""
    root = tmp_path / "image"
    root.mkdir()
    (root / "Dockerfile").write_text("FROM python:3.12-slim\nUSER app\n", encoding="utf-8")
    return root


class TestNamingAPackDoesNotMakeItApply:
    """`--pack python` selects a catalog; it does not make the path Python.

    Selecting packs by name is a filter on the catalog, so the two selection
    routes -- auto-detection and an explicit `--pack` -- must not disagree
    about whether the same path was examined.
    """

    def test_the_engine_marks_a_named_pack_that_cannot_handle_the_path_unexamined(
        self, unhandled_project: Path
    ):
        engine = Engine()
        engine.discover_packs()

        result = engine.check_result(unhandled_project, pack_names=["python"])

        assert result.examined is False
        assert result.findings == []

    def test_the_text_renderer_says_nothing_was_examined(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["check", str(unhandled_project), "--pack", "python"])

        assert "Structurally sound" not in result.output
        assert NOTHING_EXAMINED in result.output
        assert "matched an installed pack" in result.output

    @pytest.mark.parametrize("severity", ["error", "warn", "info"])
    def test_it_exits_two_at_every_severity(self, unhandled_project: Path, severity: str):
        result = CliRunner().invoke(
            main,
            [
                "check",
                str(unhandled_project),
                "--pack",
                "python",
                "--severity",
                severity,
                "--exit-code",
            ],
        )

        assert result.exit_code == 2

    def test_the_json_document_records_it(self, unhandled_project: Path):
        result = CliRunner().invoke(
            main, ["check", str(unhandled_project), "--pack", "python", "--format", "json"]
        )

        payload = json.loads(result.stdout)
        assert payload["examined"] is False
        assert payload["summary"] == NOTHING_EXAMINED

    def test_the_github_output_annotates_it(self, unhandled_project: Path):
        result = CliRunner().invoke(
            main, ["check", str(unhandled_project), "--pack", "python", "--format", "github"]
        )

        assert "::error title=Nothing examined::" in result.stdout

    def test_count_exits_two_and_keeps_the_integer_on_stdout(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["count", str(unhandled_project), "--pack", "python"])

        assert result.exit_code == 2
        assert result.stdout.strip().isdigit()
        assert "nothing was examined" in result.stderr.lower()

    def test_report_names_it_in_the_incomplete_run_block(self, unhandled_project: Path):
        result = CliRunner().invoke(main, ["report", str(unhandled_project), "--pack", "python"])

        assert result.exit_code == 2
        assert "## Incomplete run" in result.stdout
        assert "- **No language pack applies to this path**" in result.stdout
        assert "Structurally sound" not in result.stdout

    def test_the_config_pack_list_takes_the_same_route(self, dockerfile_project: Path):
        """`gaudi.toml`'s `packs` reaches `check_result` by the same argument.

        Run over a path auto-detection *would* have examined -- the ops pack
        claims the Dockerfile -- so the assertion can only be satisfied by the
        configured pack list actually being read. Over a path nothing applies
        to, both routes agree and the test would pass without reading the file.
        """
        (dockerfile_project / "gaudi.toml").write_text(
            '[gaudi]\npacks = ["python"]\n', encoding="utf-8"
        )

        result = CliRunner().invoke(main, ["check", str(dockerfile_project), "--exit-code"])

        assert result.exit_code == 2
        assert NOTHING_EXAMINED in result.output


class TestNamingAPackThatDoesApplyIsUnaffected:
    """The controls. Without them the filter above could be vacuous."""

    def test_a_named_pack_that_handles_the_path_still_examines_it(self, handled_project: Path):
        result = CliRunner().invoke(
            main, ["check", str(handled_project), "--pack", "python", "--format", "json"]
        )

        payload = json.loads(result.stdout)
        assert payload["examined"] is True
        assert payload["summary"] == "No architectural issues found. Structurally sound."

    def test_it_still_exits_zero(self, handled_project: Path):
        result = CliRunner().invoke(
            main, ["check", str(handled_project), "--pack", "python", "--exit-code"]
        )

        assert result.exit_code == 0

    def test_one_named_pack_that_applies_beside_one_that_does_not_is_examined(
        self, dockerfile_project: Path
    ):
        """`--pack python --pack ops` over a Dockerfile: ops applies, so the run looked."""
        result = CliRunner().invoke(
            main,
            [
                "check",
                str(dockerfile_project),
                "--pack",
                "python",
                "--pack",
                "ops",
                "--format",
                "json",
            ],
        )

        payload = json.loads(result.stdout)
        assert payload["examined"] is True
        assert NOTHING_EXAMINED not in payload["summary"]
