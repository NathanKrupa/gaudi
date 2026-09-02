# ABOUTME: A pack that fails to load is reported and counted, never swallowed.
# ABOUTME: A missing rule catalog must not print, serialize, or exit like a clean run.

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from gaudi.cli import main
from gaudi.engine import Engine
from gaudi.packs.ops import OpsPack
from gaudi.packs.python import PythonPack

UNPARSABLE = Path(__file__).parent / "fixtures" / "skip_accounting" / "unparsable.py.txt"

IMPORT_MESSAGE = "no module named 'libclang'"
INSTANTIATION_MESSAGE = "rule catalog is empty"


class _BrokenEntryPoint:
    """An entry point whose target cannot be imported."""

    def __init__(self, name: str = "broken", exc: Exception | None = None) -> None:
        self.name = name
        self._exc = exc if exc is not None else ImportError(IMPORT_MESSAGE)

    def load(self) -> Any:
        raise self._exc


class _UninstantiablePack:
    def __init__(self) -> None:
        raise RuntimeError(INSTANTIATION_MESSAGE)


class _UninstantiableEntryPoint:
    """An entry point that imports cleanly but whose pack class raises on construction."""

    name = "uninstantiable"

    def load(self) -> Any:
        return _UninstantiablePack


class _WorkingEntryPoint:
    def __init__(self, name: str, pack_class: type) -> None:
        self.name = name
        self._pack_class = pack_class

    def load(self) -> Any:
        return self._pack_class


class _EntryPointGroups(list):
    """Stands in for both ``entry_points()`` shapes the engine supports."""

    def get(self, group: str, default: Any = None) -> Any:
        return list(self) if group == "gaudi.packs" else (default if default is not None else [])


def _install(monkeypatch: pytest.MonkeyPatch, *eps: Any) -> None:
    """Point pack discovery at ``eps`` on every supported Python version."""

    def fake_entry_points(group: str | None = None) -> Any:
        return _EntryPointGroups(eps)

    monkeypatch.setattr("gaudi.engine.entry_points", fake_entry_points)


def _real_packs() -> tuple[Any, Any]:
    return (
        _WorkingEntryPoint("python", PythonPack),
        _WorkingEntryPoint("ops", OpsPack),
    )


def _scaffold(root: Path) -> None:
    """Write the files that satisfy every project-scope rule.

    Gaudi's project-scope rules fire on the *directory*, so a bare temp
    directory carries six findings before any module is copied in. A project
    that is meant to be clean has to be well-formed first. See
    ``tests/test_exit_code_severity.py``, which pins that this list is
    sufficient.
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
def clean_project(tmp_path: Path) -> Path:
    """A well-formed project with one module that carries no finding at any tier."""
    root = tmp_path / "project"
    root.mkdir()
    _scaffold(root)
    (root / "clean.py").write_text(
        '"""A module with nothing to report."""\n\n\ndef add(a: int, b: int) -> int:\n'
        "    return a + b\n",
        encoding="utf-8",
    )
    return root


@pytest.fixture
def skipping_project(clean_project: Path) -> Path:
    """The same well-formed project, plus one file no interpreter can parse."""
    shutil.copyfile(UNPARSABLE, clean_project / "unparsable.py")
    return clean_project


@pytest.fixture
def one_broken_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, _BrokenEntryPoint(), *_real_packs())


@pytest.fixture
def all_packs_load(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, *_real_packs())


class TestEngineRecordsPackErrors:
    def test_a_pack_that_cannot_be_imported_is_recorded_with_its_error(self, one_broken_pack: None):
        engine = Engine()
        engine.discover_packs()

        recorded = {e.pack: e.error for e in engine.pack_errors}
        assert list(recorded) == ["broken"]
        assert "ImportError" in recorded["broken"]
        assert IMPORT_MESSAGE in recorded["broken"]

    def test_a_pack_whose_class_cannot_be_built_is_recorded_with_its_error(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        _install(monkeypatch, _UninstantiableEntryPoint(), *_real_packs())
        engine = Engine()
        engine.discover_packs()

        recorded = {e.pack: e.error for e in engine.pack_errors}
        assert list(recorded) == ["uninstantiable"]
        assert "RuntimeError" in recorded["uninstantiable"]
        assert INSTANTIATION_MESSAGE in recorded["uninstantiable"]

    def test_the_packs_that_do_load_are_still_registered(self, one_broken_pack: None):
        engine = Engine()
        engine.discover_packs()

        assert sorted(engine.packs) == ["ops", "python"]

    def test_a_discovery_where_every_pack_loads_records_no_error(self, all_packs_load: None):
        engine = Engine()
        engine.discover_packs()

        assert engine.pack_errors == []

    def test_the_real_installed_packs_load_without_error(self):
        """Control: the shipped entry points are not themselves broken."""
        engine = Engine()
        engine.discover_packs()

        assert engine.pack_errors == []
        assert engine.packs

    def test_the_failure_is_still_logged(self, one_broken_pack: None, caplog):
        """The log channel stays; it is simply no longer the only one."""
        with caplog.at_level(logging.WARNING, logger="gaudi.engine"):
            Engine().discover_packs()

        assert "broken" in caplog.text
        assert IMPORT_MESSAGE in caplog.text


class TestCheckResultCarriesPackErrors:
    def test_check_result_reports_the_failed_pack(self, one_broken_pack: None, clean_project: Path):
        engine = Engine()
        engine.discover_packs()

        result = engine.check_result(clean_project)

        assert [e.pack for e in result.pack_errors] == ["broken"]

    def test_check_result_reports_it_even_when_no_pack_could_load(
        self, monkeypatch: pytest.MonkeyPatch, clean_project: Path
    ):
        """The worst case: nothing loaded, so nothing can be detected either.

        This is the path that returns before any pack runs. If the failure is
        not attached here, a wholly broken install reports an empty result.
        """
        _install(monkeypatch, _BrokenEntryPoint())
        engine = Engine()
        engine.discover_packs()

        result = engine.check_result(clean_project)

        assert result.findings == []
        assert [e.pack for e in result.pack_errors] == ["broken"]

    def test_check_result_on_a_healthy_install_carries_no_pack_errors(
        self, all_packs_load: None, clean_project: Path
    ):
        engine = Engine()
        engine.discover_packs()

        assert engine.check_result(clean_project).pack_errors == []


class TestCliReportsPackErrors:
    def test_text_output_names_the_pack_and_the_error(
        self, one_broken_pack: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["check", str(clean_project)])

        assert "1 pack failed to load" in result.output
        assert "broken" in result.output
        assert "ImportError" in result.output

    def test_the_severity_filter_does_not_hide_a_pack_error(
        self, one_broken_pack: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["check", str(clean_project), "--severity", "error"])

        assert "1 pack failed to load" in result.output

    def test_json_output_lists_the_failed_pack(self, one_broken_pack: None, clean_project: Path):
        result = CliRunner().invoke(main, ["check", str(clean_project), "--format", "json"])

        payload = json.loads(result.output)
        assert [entry["pack"] for entry in payload["pack_errors"]] == ["broken"]
        assert IMPORT_MESSAGE in payload["pack_errors"][0]["error"]

    def test_github_output_annotates_the_failed_pack(
        self, one_broken_pack: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["check", str(clean_project), "--format", "github"])

        assert "::error title=Pack load failure::" in result.output
        assert "broken" in result.output

    def test_a_healthy_run_does_not_mention_pack_errors(
        self, all_packs_load: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["check", str(clean_project)])

        assert "failed to load" not in result.output.lower()

    def test_json_output_on_a_healthy_run_has_an_empty_pack_errors_list(
        self, all_packs_load: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["check", str(clean_project), "--format", "json"])

        assert json.loads(result.output)["pack_errors"] == []


class TestExitCode:
    def test_a_pack_error_turns_an_otherwise_clean_run_red(
        self, one_broken_pack: None, clean_project: Path
    ):
        """The negative fixture: one broken pack, clean code, no findings, exit 2."""
        result = CliRunner().invoke(main, ["check", str(clean_project), "--exit-code"])

        assert result.exit_code == 2

    @pytest.mark.parametrize("severity", ["error", "warn", "info"])
    def test_a_pack_error_exits_two_at_every_severity(
        self, one_broken_pack: None, clean_project: Path, severity: str
    ):
        result = CliRunner().invoke(
            main, ["check", str(clean_project), "--severity", severity, "--exit-code"]
        )

        assert result.exit_code == 2

    def test_a_pack_error_outranks_a_finding(
        self, monkeypatch: pytest.MonkeyPatch, clean_project: Path
    ):
        """Exit 2 wins over exit 1: the report cannot be trusted exhaustive."""
        _install(monkeypatch, _BrokenEntryPoint(), *_real_packs())
        (clean_project / "insecure.py").write_text(
            "def run(src):\n    return eval(src)\n", encoding="utf-8"
        )

        result = CliRunner().invoke(
            main, ["check", str(clean_project), "--severity", "error", "--exit-code"]
        )

        assert result.exit_code == 2

    def test_naming_the_packs_that_work_does_not_suppress_it(
        self, one_broken_pack: None, clean_project: Path
    ):
        """A pack error describes the install, not the packs the caller named."""
        result = CliRunner().invoke(
            main, ["check", str(clean_project), "--pack", "python", "--exit-code"]
        )

        assert result.exit_code == 2

    def test_a_healthy_run_still_exits_zero(self, all_packs_load: None, clean_project: Path):
        result = CliRunner().invoke(main, ["check", str(clean_project), "--exit-code"])

        assert result.exit_code == 0

    def test_a_pack_error_is_silent_without_the_exit_code_flag(
        self, one_broken_pack: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["check", str(clean_project)])

        assert result.exit_code == 0


class TestCountCannotUndercountSilently:
    """A ratchet reads `count`; a missing rule catalog reads as progress."""

    def test_a_pack_error_makes_count_exit_two(self, one_broken_pack: None, clean_project: Path):
        result = CliRunner().invoke(main, ["count", str(clean_project)])

        assert result.exit_code == 2

    def test_a_healthy_count_exits_zero(self, all_packs_load: None, clean_project: Path):
        result = CliRunner().invoke(main, ["count", str(clean_project)])

        assert result.exit_code == 0

    def test_the_integer_still_reaches_stdout(self, one_broken_pack: None, clean_project: Path):
        result = CliRunner().invoke(main, ["count", str(clean_project)])

        assert result.stdout.strip().isdigit()

    def test_the_pack_error_is_reported_off_stdout(
        self, one_broken_pack: None, clean_project: Path
    ):
        result = CliRunner().invoke(
            main, ["count", str(clean_project)], catch_exceptions=False, standalone_mode=False
        )

        assert "broken" not in result.stdout


class TestListPacksNamesWhatFailed:
    def test_a_failed_pack_is_named_rather_than_absent(self, one_broken_pack: None):
        result = CliRunner().invoke(main, ["list-packs"])

        assert "broken" in result.output
        assert "ImportError" in result.output

    def test_a_wholly_broken_install_does_not_read_as_none_installed(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """The lie this closes: 'No language packs installed' over a failed import."""
        _install(monkeypatch, _BrokenEntryPoint())

        result = CliRunner().invoke(main, ["list-packs"])

        assert "No language packs installed" not in result.output
        assert "broken" in result.output
        assert "ImportError" in result.output

    def test_a_healthy_install_does_not_mention_failures(self, all_packs_load: None):
        result = CliRunner().invoke(main, ["list-packs"])

        assert "failed to load" not in result.output.lower()


class TestReportNamesAnIncompleteRun:
    """`gaudi report` is step 2 of docs/llm-workflow.md; a lying briefing is worse than none."""

    def test_report_names_the_failed_pack(self, one_broken_pack: None, clean_project: Path):
        result = CliRunner().invoke(main, ["report", str(clean_project)])

        assert "broken" in result.output
        assert "ImportError" in result.output

    def test_report_does_not_call_an_incomplete_run_structurally_sound(
        self, one_broken_pack: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["report", str(clean_project)])

        assert "Structurally sound" not in result.output

    def test_report_exits_two_on_a_pack_error(self, one_broken_pack: None, clean_project: Path):
        result = CliRunner().invoke(main, ["report", str(clean_project)])

        assert result.exit_code == 2

    def test_report_names_a_skipped_file(self, all_packs_load: None, skipping_project: Path):
        result = CliRunner().invoke(main, ["report", str(skipping_project)])

        assert "unparsable.py" in result.output
        assert result.exit_code == 2

    def test_the_markdown_still_reaches_the_output_file(
        self, one_broken_pack: None, clean_project: Path, tmp_path: Path
    ):
        """The briefing is still the best available answer; the exit code says it is partial."""
        destination = tmp_path / "report.md"

        result = CliRunner().invoke(
            main, ["report", str(clean_project), "--output", str(destination)]
        )

        assert result.exit_code == 2
        assert "broken" in destination.read_text(encoding="utf-8")

    def test_a_healthy_report_still_says_structurally_sound(
        self, all_packs_load: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["report", str(clean_project)])

        assert "Structurally sound" in result.output
        assert result.exit_code == 0

    def test_a_healthy_report_does_not_mention_an_incomplete_run(
        self, all_packs_load: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["report", str(clean_project)])

        assert "Incomplete run" not in result.output


class TestNamingTheFailedPackOnTheCommandLine:
    """`--pack <broken>` used to exit 1 as 'Unknown pack(s)' -- a misdiagnosis."""

    def test_naming_the_failed_pack_reports_it_as_a_pack_error(
        self, one_broken_pack: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["check", str(clean_project), "--pack", "broken"])

        assert result.exit_code == 2
        assert "ImportError" in result.output
        assert "Unknown pack" not in result.output

    def test_naming_the_failed_pack_on_a_wholly_broken_install(
        self, monkeypatch: pytest.MonkeyPatch, clean_project: Path
    ):
        _install(monkeypatch, _BrokenEntryPoint())

        result = CliRunner().invoke(main, ["check", str(clean_project), "--pack", "broken"])

        assert result.exit_code == 2
        assert "none installed" not in result.output
        assert "ImportError" in result.output

    def test_an_unknown_pack_over_a_broken_install_is_not_called_none_installed(
        self, monkeypatch: pytest.MonkeyPatch, clean_project: Path
    ):
        """'none installed' sends the reader to install what is already there."""
        _install(monkeypatch, _BrokenEntryPoint())

        result = CliRunner().invoke(main, ["check", str(clean_project), "--pack", "rust"])

        assert result.exit_code == 1
        assert "none installed" not in result.output
        assert "broken" in result.output

    def test_a_truly_unknown_pack_still_exits_one(self, all_packs_load: None, clean_project: Path):
        """The control: an unknown name is a caller error, not an incomplete run."""
        result = CliRunner().invoke(main, ["check", str(clean_project), "--pack", "rust"])

        assert result.exit_code == 1
        assert "Unknown pack(s): rust" in result.output

    def test_count_reports_the_named_failed_pack_too(
        self, one_broken_pack: None, clean_project: Path
    ):
        """Every command routes through _run_check, so none of them can misdiagnose it."""
        result = CliRunner().invoke(main, ["count", str(clean_project), "--pack", "broken"])

        assert result.exit_code == 2

    def test_naming_a_pack_that_loaded_is_unaffected(
        self, one_broken_pack: None, clean_project: Path
    ):
        """The control: a working pack named on the command line still runs."""
        result = CliRunner().invoke(main, ["check", str(clean_project), "--pack", "python"])

        assert "Unknown pack" not in result.output


class TestCountNamesWhatItCouldNotCount:
    """A stderr block nothing asserts on is a block that can be deleted silently."""

    def test_the_pack_error_names_the_pack_and_the_error_on_stderr(
        self, one_broken_pack: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["count", str(clean_project)])

        assert "broken" in result.stderr
        assert IMPORT_MESSAGE in result.stderr
        assert "undercount" in result.stderr

    def test_the_skip_reason_names_the_file_on_stderr(
        self, all_packs_load: None, skipping_project: Path
    ):
        result = CliRunner().invoke(main, ["count", str(skipping_project)])

        assert "unparsable.py" in result.stderr
        assert "syntax" in result.stderr.lower()
        assert "undercount" in result.stderr

    def test_a_healthy_count_says_nothing_on_stderr(
        self, all_packs_load: None, clean_project: Path
    ):
        result = CliRunner().invoke(main, ["count", str(clean_project)])

        assert result.stderr == ""
