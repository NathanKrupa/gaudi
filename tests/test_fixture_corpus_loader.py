# ABOUTME: Unit tests for the fixture corpus loader (single-file and multi-file fixtures).
# ABOUTME: Exercises _cases_for_rule_dir and fixture_as_project against synthetic rule directories.
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.fixture_corpus import (
    FixtureCase,
    _cases_for_rule_dir,
    fixture_as_project,
)


def _write_rule_dir(
    root: Path, rule_id: str, expected: dict, files: dict[str, str]
) -> Path:
    rule_dir = root / rule_id
    rule_dir.mkdir(parents=True)
    (rule_dir / "expected.json").write_text(json.dumps(expected), encoding="utf-8")
    for relpath, content in files.items():
        target = rule_dir / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return rule_dir


class TestSingleFileFixtures:
    def test_loads_single_file_case(self, tmp_path: Path) -> None:
        rule_dir = _write_rule_dir(
            tmp_path,
            "DEMO-001",
            {
                "rule_id": "DEMO-001",
                "fixtures": {
                    "fail_thing.py": {
                        "expected_findings": [
                            {"severity": "warning", "message_contains": "boom"}
                        ]
                    },
                    "pass_thing.py": {"expected_findings": []},
                },
            },
            {
                "fail_thing.py": "x = 1\n",
                "pass_thing.py": "y = 2\n",
            },
        )

        cases = _cases_for_rule_dir(rule_dir)

        assert {c.name for c in cases} == {"fail_thing.py", "pass_thing.py"}
        fail = next(c for c in cases if c.is_fail)
        assert not fail.is_directory, "single-file fixture should not report as directory"
        assert fail.expected[0].message_contains == "boom"

    def test_fixture_as_project_strips_prefix(self, tmp_path: Path) -> None:
        rule_dir = _write_rule_dir(
            tmp_path,
            "DEMO-002",
            {
                "rule_id": "DEMO-002",
                "fixtures": {"fail_thing.py": {"expected_findings": []}},
            },
            {"fail_thing.py": "x = 1\n"},
        )
        case = _cases_for_rule_dir(rule_dir)[0]

        with fixture_as_project(case) as project_root:
            assert (project_root / "thing.py").read_text(encoding="utf-8") == "x = 1\n"
            assert not (project_root / "fail_thing.py").exists(), "fail_ prefix should be stripped from copied path"
            assert (project_root / "pyproject.toml").exists()


class TestMultiFileFixtures:
    def test_loads_directory_case(self, tmp_path: Path) -> None:
        rule_dir = _write_rule_dir(
            tmp_path,
            "DEMO-003",
            {
                "rule_id": "DEMO-003",
                "fixtures": {
                    "fail_branched": {
                        "expected_findings": [
                            {"severity": "error", "message_contains": "diverged"}
                        ]
                    },
                    "pass_linear": {"expected_findings": []},
                },
            },
            {
                "fail_branched/pkg/a.py": "a = 1\n",
                "fail_branched/pkg/b.py": "b = 2\n",
                "pass_linear/pkg/a.py": "a = 1\n",
            },
        )

        cases = _cases_for_rule_dir(rule_dir)

        by_name = {c.name: c for c in cases}
        assert set(by_name) == {"fail_branched", "pass_linear"}
        assert by_name["fail_branched"].is_directory
        assert by_name["fail_branched"].is_fail
        assert by_name["pass_linear"].is_directory
        assert by_name["pass_linear"].is_pass

    def test_directory_key_with_trailing_slash(self, tmp_path: Path) -> None:
        rule_dir = _write_rule_dir(
            tmp_path,
            "DEMO-004",
            {
                "rule_id": "DEMO-004",
                "fixtures": {"fail_branched/": {"expected_findings": []}},
            },
            {"fail_branched/x.py": "x = 1\n"},
        )

        cases = _cases_for_rule_dir(rule_dir)
        assert len(cases) == 1
        assert cases[0].name == "fail_branched"
        assert cases[0].is_directory

    def test_fixture_as_project_copies_tree(self, tmp_path: Path) -> None:
        rule_dir = _write_rule_dir(
            tmp_path,
            "DEMO-005",
            {
                "rule_id": "DEMO-005",
                "fixtures": {"fail_branched": {"expected_findings": []}},
            },
            {
                "fail_branched/alembic/versions/a.py": "revision = 'a'\n",
                "fail_branched/alembic/versions/b.py": "revision = 'b'\n",
            },
        )
        case = _cases_for_rule_dir(rule_dir)[0]

        with fixture_as_project(case) as project_root:
            assert (project_root / "alembic" / "versions" / "a.py").read_text(
                encoding="utf-8"
            ) == "revision = 'a'\n"
            assert (project_root / "alembic" / "versions" / "b.py").read_text(
                encoding="utf-8"
            ) == "revision = 'b'\n"
            # The fail_ prefix is NOT preserved at the project root.
            assert not (project_root / "fail_branched").exists(), "directory fixture wrapper should not appear in temp project"
            assert (project_root / "pyproject.toml").exists()

    def test_mixed_single_and_multi_in_one_rule(self, tmp_path: Path) -> None:
        rule_dir = _write_rule_dir(
            tmp_path,
            "DEMO-006",
            {
                "rule_id": "DEMO-006",
                "fixtures": {
                    "fail_simple.py": {"expected_findings": []},
                    "fail_complex": {"expected_findings": []},
                },
            },
            {
                "fail_simple.py": "x = 1\n",
                "fail_complex/a.py": "a = 1\n",
                "fail_complex/b.py": "b = 2\n",
            },
        )

        cases = _cases_for_rule_dir(rule_dir)
        by_name = {c.name: c for c in cases}
        assert by_name["fail_simple.py"].is_directory is False
        assert by_name["fail_complex"].is_directory is True


class TestErrors:
    def test_missing_fixture_path_raises(self, tmp_path: Path) -> None:
        rule_dir = _write_rule_dir(
            tmp_path,
            "DEMO-007",
            {
                "rule_id": "DEMO-007",
                "fixtures": {"fail_missing.py": {"expected_findings": []}},
            },
            {},
        )
        with pytest.raises(FileNotFoundError):
            _cases_for_rule_dir(rule_dir)
