"""Tests for packaging rules (STRUCT-010 through STRUCT-013)."""

import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack

FIXTURES = Path(__file__).parent / "fixtures"


class TestPackagingRules:
    @staticmethod
    def _findings_for(fixture_name: str, code: str):
        pack = PythonPack()
        path = FIXTURES / fixture_name
        findings = pack.check(path)
        return [f for f in findings if f.code == code]

    def test_struct_010_path_hacks(self):
        hits = self._findings_for("arch90_path_hacks.py", "STRUCT-010")
        assert len(hits) == 2

    def test_struct_011_missing_pyproject(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "STRUCT-011"]
            assert len(hits) == 1

    def test_struct_012_no_entry_point(self):
        hits = self._findings_for("arch90_no_entry_point.py", "STRUCT-012")
        assert len(hits) == 1

    def test_struct_013_no_lock_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "app.py").write_text("x = 1\n")
            (tmppath / "pyproject.toml").write_text("[project]\nname = 'test'\n")
            pack = PythonPack()
            findings = pack.check(tmppath)
            hits = [f for f in findings if f.code == "STRUCT-013"]
            assert len(hits) == 1
