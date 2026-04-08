# ABOUTME: Loader and helpers for the per-rule fixture corpus under tests/fixtures/<lang>/<RULE-ID>/.
# ABOUTME: Backs the parametrized fixture-driven test runner described in docs/testing-fixtures.md.
from __future__ import annotations

import json
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

DEFAULT_LANGUAGE = "python"
KNOWN_LANGUAGES: tuple[str, ...] = ("python", "ops")
CORPUS_ROOT = Path(__file__).parent / "fixtures"
PYTHON_CORPUS = CORPUS_ROOT / DEFAULT_LANGUAGE

_PYPROJECT_STUB = "[project]\nname = 'fixture_project'\nversion = '0.0.0'\n"


@dataclass(frozen=True)
class ExpectedFinding:
    severity: str
    message_contains: str
    line: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExpectedFinding:
        return cls(
            severity=data["severity"],
            message_contains=data["message_contains"],
            line=data.get("line"),
        )


@dataclass(frozen=True)
class FixtureCase:
    """One fixture (a single .py file or a directory of .py files) paired with expected findings."""

    rule_id: str
    rule_dir: Path
    name: str
    expected: tuple[ExpectedFinding, ...]

    @property
    def path(self) -> Path:
        return self.rule_dir / self.name

    @property
    def is_directory(self) -> bool:
        return self.path.is_dir()

    @property
    def is_pass(self) -> bool:
        return self.name.startswith("pass_")

    @property
    def is_fail(self) -> bool:
        return self.name.startswith("fail_")

    @property
    def test_id(self) -> str:
        return f"{self.rule_id}::{self.name}"


def _load_expected(rule_dir: Path) -> dict[str, Any]:
    expected_path = rule_dir / "expected.json"
    if not expected_path.exists():
        raise FileNotFoundError(
            f"Fixture directory {rule_dir} has no expected.json. "
            f"See docs/testing-fixtures.md for the schema."
        )
    return json.loads(expected_path.read_text(encoding="utf-8"))


def discover_rule_dirs(language: str = DEFAULT_LANGUAGE) -> list[Path]:
    """Return all rule directories under tests/fixtures/<language>/, sorted by rule id."""
    lang_root = CORPUS_ROOT / language
    if not lang_root.exists():
        return []
    return sorted(p for p in lang_root.iterdir() if p.is_dir())


def _cases_for_rule_dir(rule_dir: Path) -> list[FixtureCase]:
    spec = _load_expected(rule_dir)
    rule_id = spec["rule_id"]
    if rule_id != rule_dir.name:
        raise ValueError(
            f"expected.json rule_id={rule_id!r} does not match directory {rule_dir.name!r}"
        )
    cases: list[FixtureCase] = []
    for name, file_spec in spec["fixtures"].items():
        # Accept both "fail_branched/" and "fail_branched" as directory keys.
        normalized = name.rstrip("/\\")
        fixture_path = rule_dir / normalized
        if not fixture_path.exists():
            raise FileNotFoundError(f"expected.json references missing fixture {fixture_path}")
        expected = tuple(
            ExpectedFinding.from_dict(item) for item in file_spec.get("expected_findings", [])
        )
        cases.append(FixtureCase(rule_id, rule_dir, normalized, expected))
    return cases


def discover_cases(language: str = DEFAULT_LANGUAGE) -> list[FixtureCase]:
    """Discover every (rule, fixture) case in the corpus for one language tree."""
    cases: list[FixtureCase] = []
    for rule_dir in discover_rule_dirs(language):
        cases.extend(_cases_for_rule_dir(rule_dir))
    return cases


def discover_all_cases() -> list[FixtureCase]:
    """Discover cases across every known fixture tree (python, ops, ...).

    This is what the parametrized corpus test uses. Each tree is walked
    independently; the engine sorts out which pack handles which rule.
    """
    cases: list[FixtureCase] = []
    for language in KNOWN_LANGUAGES:
        cases.extend(discover_cases(language))
    return cases


def _strip_fixture_prefix(name: str) -> str:
    for prefix in ("fail_", "pass_"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


@contextmanager
def fixture_as_project(case: FixtureCase) -> Iterator[Path]:
    """Copy a fixture into a clean temporary project tree.

    Two fixture shapes are supported:

    * **Single file** (`fail_xxx.py` / `pass_xxx.py`): copied to the temp project
      root with the `fail_`/`pass_` prefix stripped, so module names look ordinary
      to rules that key on filenames. The runner synthesizes a stub `pyproject.toml`
      and empty `requirements-lock.txt` so unrelated infrastructure rules don't
      fire on the bare temp project.
    * **Multi-file directory** (`fail_xxx/` / `pass_xxx/`): the entire tree under
      the fixture directory is copied verbatim into the temp project root,
      preserving subdirectories. This lets cross-file rules (alembic head
      divergence, layering, circular imports, ...) be specified declaratively.
      Directory fixtures own their project shape -- the runner does NOT inject
      stub files. This is what makes it possible to write fail fixtures for rules
      whose subject is the *absence* of a project file (e.g. STRUCT-011 missing
      pyproject.toml, STRUCT-013 missing lock file). If a directory fixture wants
      a pyproject.toml or lock file, it must include one explicitly.

    Many rules deliberately skip paths containing 'tests' or 'fixtures', so
    fixtures cannot be analyzed in place. The temp project gives the engine a
    realistic root.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        if case.is_directory:
            # The directory fixture defines its own project shape -- copy verbatim
            # without synthesizing pyproject.toml / lock files. This is required
            # for rules that test for the absence of these files.
            shutil.copytree(case.path, tmppath, dirs_exist_ok=True)
        else:
            (tmppath / "pyproject.toml").write_text(_PYPROJECT_STUB, encoding="utf-8")
            (tmppath / "requirements-lock.txt").write_text("", encoding="utf-8")
            target_name = _strip_fixture_prefix(case.name)
            shutil.copy(case.path, tmppath / target_name)
        yield tmppath
