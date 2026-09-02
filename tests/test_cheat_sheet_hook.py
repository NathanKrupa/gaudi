# ABOUTME: Tests for scripts/lint/cheat_sheet_check.py, the checkout-correct drift guard.
# ABOUTME: Cover repo-root derivation, interpreter re-exec choice, and the loud exit-2 path.

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import ModuleType
from unittest import mock

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "lint" / "cheat_sheet_check.py"


def _load_hook() -> ModuleType:
    """Import the hook script by path — it lives outside the package."""
    spec = importlib.util.spec_from_file_location("cheat_sheet_check", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = _load_hook()


def test_repo_root_is_the_checkout_holding_this_script():
    """The root is derived from __file__, so it is the tree being committed."""
    root = hook.repo_root()
    assert (root / "src" / "gaudi" / "cli.py").is_file()
    assert (root / "scripts" / "lint" / "cheat_sheet_check.py").is_file()


def test_artifact_resolves_under_the_repo_root():
    assert (hook.repo_root() / hook.ARTIFACT).is_file()


def test_venv_interpreter_none_when_checkout_has_no_venv(tmp_path: Path):
    assert hook.venv_interpreter(tmp_path) is None


@pytest.mark.parametrize("relative", ["bin/python", "Scripts/python.exe"])
def test_venv_interpreter_finds_posix_and_windows_layouts(tmp_path: Path, relative: str):
    candidate = tmp_path / ".venv" / relative
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    assert hook.venv_interpreter(tmp_path) == candidate


def _make_venv(root: Path) -> Path:
    candidate = root / ".venv" / "bin" / "python"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    return candidate


def test_reexec_target_prefers_the_checkouts_own_venv(tmp_path: Path):
    candidate = _make_venv(tmp_path)
    assert hook.reexec_target(tmp_path, {}, "/usr/bin/python3") == candidate


def test_reexec_target_none_when_guard_variable_is_set(tmp_path: Path):
    """The child never re-execs again, so a missing dependency cannot loop."""
    _make_venv(tmp_path)
    assert hook.reexec_target(tmp_path, {hook._REEXEC_ENV: "1"}, "/usr/bin/python3") is None


def test_reexec_target_none_when_already_running_that_interpreter(tmp_path: Path):
    candidate = _make_venv(tmp_path)
    assert hook.reexec_target(tmp_path, {}, str(candidate)) is None


def test_reexec_target_none_when_checkout_has_no_venv(tmp_path: Path):
    assert hook.reexec_target(tmp_path, {}, "/usr/bin/python3") is None


@pytest.fixture
def isolated_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Run main() against an empty checkout without leaking cwd or sys.path."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv(hook._REEXEC_ENV, "1")
    monkeypatch.setattr(hook, "repo_root", lambda: tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_unimportable_gaudi_exits_two_and_says_why(isolated_run: Path, capsys):
    """'Could not look' must never exit the same as 'cheat-sheet is current'."""
    with mock.patch.dict(sys.modules, {"gaudi.cli": None}):
        assert hook.main([]) == 2
    stderr = capsys.readouterr().err
    assert "COULD NOT LOOK" in stderr
    assert str(isolated_run / "src") in stderr


def test_delegates_to_the_cli_and_returns_its_exit_code(isolated_run: Path):
    calls: list[dict[str, object]] = []

    def fake_main(**kwargs: object) -> None:
        calls.append(kwargs)
        raise SystemExit(7)

    stub = types.ModuleType("gaudi.cli")
    stub.main = types.SimpleNamespace(main=fake_main)  # type: ignore[attr-defined]

    with mock.patch.dict(sys.modules, {"gaudi.cli": stub}):
        assert hook.main([]) == 7

    assert calls[0]["args"] == ["cheat-sheet", "--check", "-o", str(hook.ARTIFACT)]


def test_prepends_this_checkouts_src_ahead_of_pythonpath(isolated_run: Path):
    stub = types.ModuleType("gaudi.cli")
    stub.main = types.SimpleNamespace(main=lambda **_: None)  # type: ignore[attr-defined]

    with mock.patch.dict(sys.modules, {"gaudi.cli": stub}):
        assert hook.main([]) == 0

    assert sys.path[0] == str(isolated_run / "src")


def test_anchors_cwd_to_the_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The artifact path is relative, so the cwd decides which file is measured."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setenv(hook._REEXEC_ENV, "1")
    monkeypatch.setattr(hook, "repo_root", lambda: tmp_path)
    monkeypatch.chdir(elsewhere)

    stub = types.ModuleType("gaudi.cli")
    stub.main = types.SimpleNamespace(main=lambda **_: None)  # type: ignore[attr-defined]

    with mock.patch.dict(sys.modules, {"gaudi.cli": stub}):
        assert hook.main([]) == 0

    assert Path.cwd().resolve() == tmp_path.resolve()
