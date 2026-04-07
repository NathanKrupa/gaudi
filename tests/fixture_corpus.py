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

CORPUS_ROOT = Path(__file__).parent / "fixtures"
PYTHON_CORPUS = CORPUS_ROOT / "python"

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
    """One fixture file paired with its expected findings."""

    rule_id: str
    rule_dir: Path
    filename: str
    expected: tuple[ExpectedFinding, ...]

    @property
    def path(self) -> Path:
        return self.rule_dir / self.filename

    @property
    def is_pass(self) -> bool:
        return self.filename.startswith("pass_")

    @property
    def is_fail(self) -> bool:
        return self.filename.startswith("fail_")

    @property
    def test_id(self) -> str:
        return f"{self.rule_id}::{self.filename}"


def _load_expected(rule_dir: Path) -> dict[str, Any]:
    expected_path = rule_dir / "expected.json"
    if not expected_path.exists():
        raise FileNotFoundError(
            f"Fixture directory {rule_dir} has no expected.json. "
            f"See docs/testing-fixtures.md for the schema."
        )
    return json.loads(expected_path.read_text(encoding="utf-8"))


def discover_rule_dirs(language: str = "python") -> list[Path]:
    """Return all rule directories under tests/fixtures/<language>/, sorted by rule id."""
    lang_root = CORPUS_ROOT / language
    if not lang_root.exists():
        return []
    return sorted(p for p in lang_root.iterdir() if p.is_dir())


def discover_cases(language: str = "python") -> list[FixtureCase]:
    """Discover every (rule, fixture-file) case in the corpus for parametrized tests."""
    cases: list[FixtureCase] = []
    for rule_dir in discover_rule_dirs(language):
        spec = _load_expected(rule_dir)
        rule_id = spec["rule_id"]
        if rule_id != rule_dir.name:
            raise ValueError(
                f"expected.json rule_id={rule_id!r} does not match directory {rule_dir.name!r}"
            )
        for filename, file_spec in spec["fixtures"].items():
            expected = tuple(
                ExpectedFinding.from_dict(item) for item in file_spec.get("expected_findings", [])
            )
            fixture_path = rule_dir / filename
            if not fixture_path.exists():
                raise FileNotFoundError(f"expected.json references missing fixture {fixture_path}")
            cases.append(
                FixtureCase(
                    rule_id=rule_id,
                    rule_dir=rule_dir,
                    filename=filename,
                    expected=expected,
                )
            )
    return cases


@contextmanager
def fixture_as_project(case: FixtureCase) -> Iterator[Path]:
    """Copy a fixture file into a clean temporary project tree.

    Many rules deliberately skip paths containing 'tests' or 'fixtures', so
    fixtures cannot be analyzed in place. The temp project gives the engine a
    realistic root with a `pyproject.toml` and the fixture file at the top level.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / "pyproject.toml").write_text(_PYPROJECT_STUB, encoding="utf-8")
        (tmppath / "requirements-lock.txt").write_text("", encoding="utf-8")
        # Strip any leading "fail_"/"pass_" so module names look ordinary; some rules
        # key on filenames or dunder layout.
        target_name = case.filename
        for prefix in ("fail_", "pass_"):
            if target_name.startswith(prefix):
                target_name = target_name[len(prefix) :]
                break
        shutil.copy(case.path, tmppath / target_name)
        yield tmppath
