# ABOUTME: Tests for dependency graph rules (DEP-001 through DEP-004).
# ABOUTME: Covers circular imports, fan-out, fan-in, and unstable dependencies.
"""Tests for dependency graph rules."""

import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack


def _check_project(files: dict[str, str]) -> list:
    """Create a temp project with given files and run all rules."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "pyproject.toml").write_text('[project]\nname = "myapp"\n')
        for name, source in files.items():
            filepath = root / name
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(source)
        pack = PythonPack()
        return pack.check(root)


def _hits(findings: list, code: str) -> list:
    return [f for f in findings if f.code == code]


# ---------------------------------------------------------------
# DEP-001  CircularImport
# ---------------------------------------------------------------


class TestCircularImport:
    def test_direct_cycle_detected(self):
        """A imports B, B imports A — should fire."""
        findings = _check_project(
            {
                "a.py": "import b\nx = 1\n",
                "b.py": "import a\ny = 2\n",
            }
        )
        hits = _hits(findings, "DEP-001")
        assert len(hits) >= 1

    def test_three_node_cycle_detected(self):
        """A→B→C→A cycle — should fire."""
        findings = _check_project(
            {
                "a.py": "import b\n",
                "b.py": "import c\n",
                "c.py": "import a\n",
            }
        )
        hits = _hits(findings, "DEP-001")
        assert len(hits) >= 1

    def test_no_cycle(self):
        """Linear chain A→B→C — should not fire."""
        findings = _check_project(
            {
                "a.py": "import b\n",
                "b.py": "import c\n",
                "c.py": "x = 1\n",
            }
        )
        hits = _hits(findings, "DEP-001")
        assert len(hits) == 0

    def test_stdlib_imports_ignored(self):
        """Imports of stdlib modules shouldn't create false cycles."""
        findings = _check_project(
            {
                "a.py": "import os\nimport sys\n",
                "b.py": "import os\nimport json\n",
            }
        )
        hits = _hits(findings, "DEP-001")
        assert len(hits) == 0

    def test_package_imports_cycle(self):
        """from pkg.mod import x style cycle — should fire."""
        findings = _check_project(
            {
                "pkg/__init__.py": "",
                "pkg/mod_a.py": "from pkg import mod_b\n",
                "pkg/mod_b.py": "from pkg import mod_a\n",
            }
        )
        hits = _hits(findings, "DEP-001")
        assert len(hits) >= 1


# ---------------------------------------------------------------
# DEP-002  FanOutExplosion
# ---------------------------------------------------------------


class TestFanOutExplosion:
    def test_high_fan_out_fires(self):
        """Module importing 10+ internal modules should trigger."""
        internal_modules = {f"mod_{i}.py": f"x = {i}\n" for i in range(12)}
        imports = "\n".join(f"import mod_{i}" for i in range(12))
        internal_modules["hub.py"] = imports + "\n"
        findings = _check_project(internal_modules)
        hits = _hits(findings, "DEP-002")
        assert len(hits) >= 1

    def test_low_fan_out_clean(self):
        """Module importing only a few internal modules — should not fire."""
        findings = _check_project(
            {
                "main.py": "import utils\nimport config\n",
                "utils.py": "x = 1\n",
                "config.py": "y = 2\n",
            }
        )
        hits = _hits(findings, "DEP-002")
        assert len(hits) == 0

    def test_stdlib_not_counted(self):
        """stdlib imports shouldn't count toward fan-out."""
        source = "\n".join(
            f"import {m}"
            for m in [
                "os",
                "sys",
                "json",
                "pathlib",
                "typing",
                "dataclasses",
                "collections",
                "functools",
                "itertools",
                "re",
                "hashlib",
                "math",
            ]
        )
        findings = _check_project({"app.py": source + "\n"})
        hits = _hits(findings, "DEP-002")
        assert len(hits) == 0


# ---------------------------------------------------------------
# DEP-003  FanInConcentration
# ---------------------------------------------------------------


class TestFanInConcentration:
    def test_hub_module_fires(self):
        """Module imported by 80%+ of project files — should fire."""
        files = {"shared.py": "CONST = 42\n"}
        # 10 files all importing shared
        for i in range(10):
            files[f"mod_{i}.py"] = "import shared\nx = 1\n"
        findings = _check_project(files)
        hits = _hits(findings, "DEP-003")
        assert len(hits) >= 1

    def test_normal_import_pattern_clean(self):
        """Module imported by a few files — should not fire."""
        findings = _check_project(
            {
                "utils.py": "x = 1\n",
                "a.py": "import utils\n",
                "b.py": "import utils\n",
                "c.py": "x = 1\n",
                "d.py": "x = 1\n",
                "e.py": "x = 1\n",
            }
        )
        hits = _hits(findings, "DEP-003")
        assert len(hits) == 0

    def test_small_project_not_triggered(self):
        """Projects with < 5 files shouldn't trigger (not meaningful)."""
        findings = _check_project(
            {
                "utils.py": "x = 1\n",
                "a.py": "import utils\n",
                "b.py": "import utils\n",
            }
        )
        hits = _hits(findings, "DEP-003")
        assert len(hits) == 0


# ---------------------------------------------------------------
# DEP-004  UnstableDependency
# ---------------------------------------------------------------


class TestUnstableDependency:
    def test_unstable_hub_fires(self):
        """High-instability module with high fan-in — should fire."""
        # "hub" imports many things (high fan-out → high instability)
        # AND many modules depend on it (high fan-in)
        files = {}
        # Create leaf modules
        for i in range(8):
            files[f"leaf_{i}.py"] = "x = 1\n"
        # hub imports many leaves (high fan-out)
        hub_imports = "\n".join(f"import leaf_{i}" for i in range(8))
        files["hub.py"] = hub_imports + "\n"
        # Many modules depend on hub (high fan-in)
        for i in range(8):
            files[f"consumer_{i}.py"] = "import hub\nx = 1\n"
        findings = _check_project(files)
        hits = _hits(findings, "DEP-004")
        assert len(hits) >= 1

    def test_stable_hub_clean(self):
        """Module with high fan-in but low fan-out (stable) — should not fire."""
        files = {"constants.py": "X = 1\nY = 2\n"}
        for i in range(8):
            files[f"mod_{i}.py"] = "import constants\nx = 1\n"
        findings = _check_project(files)
        hits = _hits(findings, "DEP-004")
        assert len(hits) == 0

    def test_small_project_not_triggered(self):
        """Projects with < 5 files shouldn't trigger."""
        findings = _check_project(
            {
                "a.py": "import b\n",
                "b.py": "import a\n",
            }
        )
        hits = _hits(findings, "DEP-004")
        assert len(hits) == 0
