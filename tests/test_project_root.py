# ABOUTME: Project-level rules and gaudi.toml resolve against the project root, not the checked path.
# ABOUTME: Pointing `check` at a subdirectory must not invent findings the project already answers.

from __future__ import annotations

from pathlib import Path

import pytest

from gaudi.config import load_config
from gaudi.packs.python.pack import PythonPack
from gaudi.project import find_config_file, find_project_root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A project whose root carries pyproject.toml + uv.lock, with a nested app."""
    root = tmp_path / "repo"
    (root / "apps" / "billing").mkdir(parents=True)
    (root / "pyproject.toml").write_text('[project]\nname = "repo"\n', encoding="utf-8")
    (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    (root / "apps" / "billing" / "views.py").write_text(
        "def index() -> str:\n    return 'ok'\n", encoding="utf-8"
    )
    return root


class TestFindProjectRoot:
    def test_a_subdirectory_resolves_to_the_project_root(self, project: Path):
        assert find_project_root(project / "apps" / "billing") == project

    def test_the_root_resolves_to_itself(self, project: Path):
        assert find_project_root(project) == project

    def test_a_nested_package_with_its_own_marker_is_its_own_root(self, project: Path):
        """A monorepo member owns its packaging; the nearest marker wins."""
        member = project / "apps" / "billing"
        (member / "pyproject.toml").write_text('[project]\nname = "billing"\n', encoding="utf-8")

        assert find_project_root(member) == member

    def test_a_directory_with_no_markers_anywhere_resolves_to_itself(self, tmp_path: Path):
        orphan = tmp_path / "loose"
        orphan.mkdir()

        assert find_project_root(orphan) == orphan

    def test_a_git_directory_alone_marks_the_root(self, tmp_path: Path):
        root = tmp_path / "repo"
        (root / ".git").mkdir(parents=True)
        (root / "pkg").mkdir()

        assert find_project_root(root / "pkg") == root


class TestProjectLevelRulesUseTheRoot:
    def test_struct_011_does_not_fire_on_a_subdirectory_of_a_packaged_project(self, project: Path):
        codes = {f.code for f in PythonPack().check(project / "apps" / "billing")}

        assert "STRUCT-011" not in codes

    def test_struct_013_does_not_fire_on_a_subdirectory_of_a_locked_project(self, project: Path):
        codes = {f.code for f in PythonPack().check(project / "apps" / "billing")}

        assert "STRUCT-013" not in codes

    def test_struct_011_still_fires_on_a_project_that_really_has_no_pyproject(self, tmp_path: Path):
        root = tmp_path / "bare"
        root.mkdir()
        (root / "app.py").write_text("x = 1\n", encoding="utf-8")

        assert "STRUCT-011" in {f.code for f in PythonPack().check(root)}

    def test_struct_013_still_fires_on_a_project_that_really_has_no_lock_file(self, tmp_path: Path):
        root = tmp_path / "bare"
        root.mkdir()
        (root / "pyproject.toml").write_text('[project]\nname = "bare"\n', encoding="utf-8")
        (root / "app.py").write_text("x = 1\n", encoding="utf-8")

        assert "STRUCT-013" in {f.code for f in PythonPack().check(root)}


class TestUvLockIsALockFile:
    def test_uv_lock_satisfies_struct_013(self, tmp_path: Path):
        root = tmp_path / "uvproj"
        root.mkdir()
        (root / "pyproject.toml").write_text('[project]\nname = "uvproj"\n', encoding="utf-8")
        (root / "uv.lock").write_text("version = 1\n", encoding="utf-8")
        (root / "app.py").write_text("x = 1\n", encoding="utf-8")

        assert "STRUCT-013" not in {f.code for f in PythonPack().check(root)}


class TestConfigParentWalk:
    def test_gaudi_toml_is_found_from_a_subdirectory(self, project: Path):
        (project / "gaudi.toml").write_text('[philosophy]\nschool = "unix"\n', encoding="utf-8")

        config = load_config(project / "apps" / "billing")

        assert config["philosophy"]["school"] == "unix"

    def test_the_nearest_gaudi_toml_wins(self, project: Path):
        (project / "gaudi.toml").write_text('[philosophy]\nschool = "unix"\n', encoding="utf-8")
        (project / "apps" / "billing" / "gaudi.toml").write_text(
            '[philosophy]\nschool = "functional"\n', encoding="utf-8"
        )

        config = load_config(project / "apps" / "billing")

        assert config["philosophy"]["school"] == "functional"

    def test_the_walk_stops_at_the_project_root(self, project: Path):
        """A gaudi.toml outside the project must not be adopted by it."""
        (project.parent / "gaudi.toml").write_text(
            '[philosophy]\nschool = "unix"\n', encoding="utf-8"
        )

        assert find_config_file(project / "apps" / "billing", "gaudi.toml") is None

    def test_no_config_anywhere_yields_defaults(self, project: Path):
        assert load_config(project / "apps" / "billing")["philosophy"]["school"] == "classical"
