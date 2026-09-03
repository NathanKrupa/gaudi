# ABOUTME: Green is part of the "Structurally sound" claim, so an incomplete run must not get it.
# ABOUTME: Pins the verdict colour of `check`'s text renderer in all four run states.

from __future__ import annotations

import io
import shutil
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from rich.console import Console

import gaudi.cli
from gaudi.cli import main
from gaudi.packs.ops import OpsPack
from gaudi.packs.python import PythonPack

UNPARSABLE = Path(__file__).parent / "fixtures" / "skip_accounting" / "unparsable.py.txt"

GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"


def styled_check(args: list[str]) -> str:
    """Run `check` against a console that emits colour, and return what it wrote.

    Rich turns colour off when its file is not a terminal, and under
    ``CliRunner`` it never is -- which is why the verdict colour went
    unmeasured. The module-level console is swapped for one told to render
    styles regardless, so the SGR codes reach the assertion.
    """
    buffer = io.StringIO()
    forced = Console(
        file=buffer,
        force_terminal=True,
        color_system="truecolor",
        width=100,
        legacy_windows=False,
    )
    original = gaudi.cli.console
    gaudi.cli.console = forced
    try:
        CliRunner().invoke(main, ["check", *args], catch_exceptions=False)
    except SystemExit:
        pass
    finally:
        gaudi.cli.console = original
    return buffer.getvalue()


def _scaffold(root: Path) -> None:
    """Write the files that satisfy every project-scope rule.

    Gaudi's project-scope rules fire on the *directory*, so a bare temp
    directory carries six findings before any module is copied in. A run that
    is meant to be clean has to be well-formed first.
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
    """The same clean project, plus one file no interpreter can parse."""
    shutil.copyfile(UNPARSABLE, clean_project / "unparsable.py")
    return clean_project


@pytest.fixture
def unhandled_project(tmp_path: Path) -> Path:
    """A directory holding nothing any installed pack claims."""
    root = tmp_path / "prose"
    root.mkdir()
    (root / "notes.txt").write_text("just some notes\n", encoding="utf-8")
    return root


class _BrokenEntryPoint:
    name = "broken"

    def load(self) -> Any:
        raise ImportError("no module named 'libclang'")


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


@pytest.fixture
def one_broken_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    eps = (
        _BrokenEntryPoint(),
        _WorkingEntryPoint("python", PythonPack),
        _WorkingEntryPoint("ops", OpsPack),
    )
    monkeypatch.setattr("gaudi.engine.entry_points", lambda group=None: _EntryPointGroups(eps))


class TestOnlyACompleteRunGetsGreen:
    """Pins, not seen-red guards: the colour is already right, and nothing measured it.

    ``check``'s comment calls green part of the "Structurally sound" claim, so
    an assertion has to hold it -- a comment asserting an invariant is part of
    the security surface. Their proof is the mutation pass: `complete = True`
    survived the whole suite before this file existed.
    """

    def test_a_complete_clean_run_is_green(self, clean_project: Path):
        styled = styled_check([str(clean_project)])

        assert GREEN in styled
        assert "Structurally sound" in styled

    def test_a_run_that_examined_nothing_is_not_green(self, unhandled_project: Path):
        styled = styled_check([str(unhandled_project)])

        assert GREEN not in styled
        assert YELLOW in styled

    def test_a_run_with_a_skipped_file_is_not_green(self, skipping_project: Path):
        styled = styled_check([str(skipping_project)])

        assert GREEN not in styled
        assert YELLOW in styled

    def test_a_run_with_a_failed_pack_is_not_green(
        self, one_broken_pack: None, clean_project: Path
    ):
        styled = styled_check([str(clean_project)])

        assert GREEN not in styled
        assert YELLOW in styled
